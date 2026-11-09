package kr.deepsight;

import org.junit.jupiter.api.*;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.core.env.Environment;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

import java.nio.file.*;
import java.util.*;
import java.net.*;
import java.net.http.*;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest(
        webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT
)
class WorkflowTest {

    @Autowired
    FilesService f;

    @Autowired
    Environment env;

    @Autowired
    Datasets datasets;

    @Autowired
    Images images;

    @Autowired
    Results results;

    @Autowired
    RunService runService;

    @Autowired
    DatasetService datasetService;

    @Autowired
    Runs runs;

    @Autowired
    Jobs jobs;

    @Autowired
    Reports reports;

    static final Path ROOT = Path.of("..")
            .toAbsolutePath()
            .normalize();

    // ============================================================
    // 테스트 환경 설정
    // ============================================================

    @DynamicPropertySource
    static void properties(DynamicPropertyRegistry r) {
        r.add(
                "spring.datasource.url",
                () -> "jdbc:h2:mem:ds;MODE=MySQL;"
                        + "DB_CLOSE_DELAY=-1;DATABASE_TO_LOWER=TRUE"
        );

        r.add("spring.datasource.username", () -> "sa");
        r.add("spring.datasource.password", () -> "");

        r.add("ds.home", () -> ROOT.toString());

        r.add(
                "ds.storage",
                () -> ROOT.resolve("build-verification/storage")
                        .normalize()
                        .toString()
        );

        r.add("ds.python", () -> "http://127.0.0.1:8091");
        r.add("ds.key", () -> "local-test-key");
    }

    // ============================================================
    // 웹 화면 및 데이터셋 조회 API 기동 확인
    // ============================================================

    @Test
    void webAndDatabaseStart() throws Exception {
        HttpClient c = HttpClient.newHttpClient();

        String base = "http://127.0.0.1:"
                + env.getProperty("local.server.port");

        assertEquals(
                200,
                c.send(
                        HttpRequest.newBuilder(
                                URI.create(base + "/")
                        ).build(),
                        HttpResponse.BodyHandlers.ofString()
                ).statusCode()
        );

        assertEquals(
                200,
                c.send(
                        HttpRequest.newBuilder(
                                URI.create(base + "/api/datasets")
                        ).build(),
                        HttpResponse.BodyHandlers.ofString()
                ).statusCode()
        );
    }

    // ============================================================
    // 저장소 밖 경로 및 잘못된 파일명 차단 확인
    // ============================================================

    @Test
    void pathAndNameChecks() {
        assertThrows(
                IllegalArgumentException.class,
                () -> f.safe("../../escape")
        );

        assertThrows(
                IllegalArgumentException.class,
                () -> FilesService.filename("../x.jpg")
        );
    }

    // ============================================================
    // 파일 변경 시 무결성 검사 실패 확인
    // ============================================================

    @Test
    void detectCorruptedArtifacts() throws Exception {
        Path dir = Files.createTempDirectory("ds-hash-");
        Path file = dir.resolve("result.csv");

        Files.writeString(file, "correct");

        var manifest = f.manifest(dir);

        f.verify(dir, manifest);

        Files.writeString(file, "tampered");

        assertThrows(
                java.io.IOException.class,
                () -> f.verify(dir, manifest)
        );

        Files.delete(file);
        Files.delete(dir);
    }

    // ============================================================
    // 실제 Python 서비스를 사용하는 통합 테스트
    // DS_FULL_TESTS=true인 경우에만 실행
    // ============================================================

    @Test
    @org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable(
            named = "DS_FULL_TESTS",
            matches = "true"
    )
    void actualPythonWorkflow() throws Exception {
        HttpClient c = HttpClient.newHttpClient();

        String base = "http://127.0.0.1:"
                + env.getProperty("local.server.port");

        // ----------------------------------------------------
        // 1. 기준 사진 20장 등록 확인
        // ----------------------------------------------------

        var sample = c.send(
                HttpRequest.newBuilder(
                                URI.create(base + "/api/datasets/sample")
                        )
                        .POST(HttpRequest.BodyPublishers.noBody())
                        .build(),
                HttpResponse.BodyHandlers.ofString()
        );

        assertEquals(200, sample.statusCode());

        var d = datasets.findById(
                f.object(sample.body()).get("id").toString()
        ).orElseThrow();

        assertEquals(
                20,
                images.findByDatasetIdOrderByFilename(d.id).size()
        );

        // ----------------------------------------------------
        // 2. 4정책 비교 실험 요청 구성
        // ----------------------------------------------------

        String id = FilesService.id();

        var body = new LinkedHashMap<String, Object>();

        body.put("requestId", id);
        body.put("datasetId", d.id);
        body.put("title", "실제 API 통합 실험");
        body.put("note", "Python 3.11.9 CPU 20장 4정책");
        body.put("previousNote", "이전 결과 보존");
        body.put("kind", "compare");
        body.put("preserve", true);
        body.put("settings", Map.of());

        // ----------------------------------------------------
        // 3. 실험 제출 및 중복 요청 처리 확인
        // ----------------------------------------------------

        var submitted = c.send(
                HttpRequest.newBuilder(
                                URI.create(base + "/api/runs")
                        )
                        .header("Content-Type", "application/json")
                        .POST(
                                HttpRequest.BodyPublishers.ofString(
                                        f.encode(body)
                                )
                        )
                        .build(),
                HttpResponse.BodyHandlers.ofString()
        );

        assertEquals(
                200,
                submitted.statusCode(),
                submitted.body()
        );

        assertEquals(id, runService.create(body).id);

        await(id);

        // 사진 20장 × 정책 4개 = 결과 80개
        assertEquals(
                80,
                results.findByRunIdOrderByFilenameAscPolicyAsc(id).size()
        );

        assertEquals(
                1,
                reports.findByRunIdOrderByRevisionDesc(id).size()
        );

        // ----------------------------------------------------
        // 4. 수동 검수 저장 확인
        // ----------------------------------------------------

        var first = results.findByRunIdOrderByFilenameAscPolicyAsc(id)
                .get(0);

        var req = HttpRequest.newBuilder(
                        URI.create(base + "/api/results/" + first.id + "/review")
                )
                .header("Content-Type", "application/json")
                .PUT(
                        HttpRequest.BodyPublishers.ofString(
                                "{\"done\":true,"
                                        + "\"missingFaces\":0,"
                                        + "\"falseFaces\":0,"
                                        + "\"quality\":\"적절함\","
                                        + "\"note\":\"실제 통합검수\"}"
                        )
                )
                .build();

        assertEquals(
                200,
                c.send(
                        req,
                        HttpResponse.BodyHandlers.ofString()
                ).statusCode()
        );

        // ----------------------------------------------------
        // 5. 검수 반영 재분석 및 보고서 개정 확인
        // ----------------------------------------------------

        runService.reanalyze(id);
        await(id);

        assertEquals(
                2,
                reports.findByRunIdOrderByRevisionDesc(id).size()
        );

        assertEquals(
                80,
                results.findByRunIdOrderByFilenameAscPolicyAsc(id).size()
        );

        var rp = reports.findByRunIdOrderByRevisionDesc(id).get(0);

        assertTrue(rp.reviewSnapshot.contains(first.id));

        assertTrue(
                Files.isDirectory(
                        f.safe("runs/" + id + "/reports/r0001")
                )
        );

        // ----------------------------------------------------
        // 6. 보고서 ZIP 다운로드 확인
        // ----------------------------------------------------

        var zip = c.send(
                HttpRequest.newBuilder(
                        URI.create(base + "/api/reports/" + rp.id + "/zip")
                ).build(),
                HttpResponse.BodyHandlers.ofByteArray()
        );

        assertEquals(200, zip.statusCode());
        assertTrue(zip.body().length > 1000);

        // ----------------------------------------------------
        // 7. 새 실험 실행 후 이전 보고서 보존 확인
        // ----------------------------------------------------

        String preservedHash = f.sha(
                f.safe(rp.rootPath + "/manifest.json")
        );

        body.put("requestId", FilesService.id());
        body.put("kind", "initial");
        body.put("title", "초기 프로그램 통합 확인");

        var next = runService.create(body);

        await(next.id);

        assertEquals(
                20,
                results.findByRunIdOrderByFilenameAscPolicyAsc(next.id)
                        .size()
        );

        assertEquals(
                preservedHash,
                f.sha(f.safe(rp.rootPath + "/manifest.json"))
        );

        assertTrue(
                Files.isRegularFile(
                        f.safe(
                                "runs/" + next.id
                                        + "/previous_preservation.json"
                        )
                )
        );
    }

    // ============================================================
    // 실험과 최신 작업이 완료될 때까지 최대 10분 대기
    // ============================================================

    void await(String id) throws Exception {
        long end = System.currentTimeMillis() + 600000;

        while (System.currentTimeMillis() < end) {
            Thread.sleep(1000);

            var r = runs.findById(id).orElseThrow();

            if (r.status.equals("COMPLETED")
                    && jobs.findByRunIdOrderByCreatedAtDesc(id)
                    .get(0)
                    .status.equals("COMPLETED")) {
                return;
            }

            if (List.of("FAILED", "IMPORT_FAILED").contains(r.status)) {
                fail(r.error);
            }
        }

        fail("작업 완료 제한 시간 초과");
    }
}