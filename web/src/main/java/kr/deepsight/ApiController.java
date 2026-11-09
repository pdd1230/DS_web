package kr.deepsight;

import org.springframework.web.bind.annotation.*;
import org.springframework.http.*;
import org.springframework.core.io.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.transaction.annotation.Transactional;

import kr.deepsight.Models.*;

import java.nio.file.*;
import java.util.*;
import java.io.*;
import java.util.zip.*;

@RestController
@RequestMapping("/api")
public class ApiController {

    // 저장소 및 서비스
    final Datasets datasets;
    final Images images;
    final Runs runs;
    final Jobs jobs;
    final Results results;
    final Reviews reviews;
    final Reports reports;
    final Artifacts artifacts;
    final Candidates candidates;
    final Faces faces;

    final DatasetService datasetService;
    final RunService runService;
    final FilesService f;
    final PythonClient python;

    public ApiController(
            Datasets d,
            Images im,
            Runs r,
            Jobs j,
            Results re,
            Reviews rv,
            Reports rp,
            Artifacts a,
            Candidates c,
            Faces fa,
            DatasetService ds,
            RunService rs,
            FilesService f,
            PythonClient p
    ) {
        datasets = d;
        images = im;
        runs = r;
        jobs = j;
        results = re;
        reviews = rv;
        reports = rp;
        artifacts = a;
        candidates = c;
        faces = fa;

        datasetService = ds;
        runService = rs;
        this.f = f;
        python = p;
    }

    // ============================================================
    // 환경 점검
    // ============================================================

    @GetMapping("/health")
    public Map<String, Object> health() {
        Map<String, Object> v = new LinkedHashMap<>();

        v.put("database", "ok");
        v.put("datasets", datasets.count());

        try {
            v.put("python", python.request("/health", null));
        } catch (Exception e) {
            v.put("pythonError", JobPoller.shortError(e));
        }

        return v;
    }

    // ============================================================
    // 데이터셋 조회 및 등록
    // ============================================================

    @GetMapping("/datasets")
    public List<Dataset> datasets() {
        return datasets.findAllByOrderByCreatedAtDesc();
    }

    @GetMapping("/datasets/{id}")
    public Map<String, Object> dataset(@PathVariable String id) {
        return Map.of(
                "dataset", datasets.findById(id).orElseThrow(),
                "images", images.findByDatasetIdOrderByFilename(id)
        );
    }

    @PostMapping("/datasets/sample")
    public Dataset sample() throws Exception {
        return datasetService.create(
                "첨부 기준 사진 20장",
                null,
                null,
                null,
                true
        );
    }

    @PostMapping(
            value = "/datasets",
            consumes = MediaType.MULTIPART_FORM_DATA_VALUE
    )
    public Dataset upload(
            @RequestParam String name,
            @RequestParam(defaultValue = "") String groundTruth,
            @RequestParam(required = false) MultipartFile gtFile,
            @RequestParam(required = false) List<MultipartFile> photos,
            @RequestParam(required = false) String parentId
    ) throws Exception {

        if (gtFile != null && !gtFile.isEmpty()) {
            groundTruth = new String(
                    gtFile.getBytes(),
                    java.nio.charset.StandardCharsets.UTF_8
            );
        }

        return datasetService.create(
                name,
                groundTruth,
                photos,
                parentId,
                false
        );
    }

    // ============================================================
    // 실험 조회 및 실행
    // ============================================================

    @GetMapping("/runs")
    public List<Run> runs() {
        return runs.findAllByOrderByCreatedAtDesc();
    }

    @PostMapping("/runs")
    public Run create(
            @RequestBody Map<String, Object> body
    ) throws Exception {
        return runService.create(body);
    }

    @GetMapping("/runs/{id}")
    public Map<String, Object> run(@PathVariable String id) {
        Run r = runs.findById(id).orElseThrow();

        return Map.of(
                "run", r,
                "jobs", jobs.findByRunIdOrderByCreatedAtDesc(id),
                "results", results.findByRunIdOrderByFilenameAscPolicyAsc(id),
                "reports", reports.findByRunIdOrderByRevisionDesc(id),
                "reviews", results.findByRunIdOrderByFilenameAscPolicyAsc(id)
                        .stream()
                        .map(x -> reviews.findByResultId(x.id))
                        .filter(Optional::isPresent)
                        .map(Optional::get)
                        .toList()
        );
    }

    @PostMapping("/runs/{id}/analyze")
    public Job analyze(@PathVariable String id) throws Exception {
        return runService.reanalyze(id);
    }

    // ============================================================
    // 작업 복구 및 로그 조회
    // ============================================================

    @PostMapping("/jobs/{id}/reimport")
    public Job reimport(@PathVariable String id) {
        Job j = jobs.findById(id).orElseThrow();

        if (!j.status.equals("IMPORT_FAILED")) {
            throw new IllegalArgumentException(
                    "DB 수집 실패 작업만 복구할 수 있습니다."
            );
        }

        j.status = "RUNNING";
        j.error = "";

        return jobs.save(j);
    }

    @GetMapping("/jobs/{id}/log")
    public Map<String, Object> log(
            @PathVariable String id
    ) throws Exception {

        Job j = jobs.findById(id).orElseThrow();

        Path p = f.safe(
                "runs/" + j.runId + "/logs/" + j.id + ".log"
        );

        String text = Files.exists(p)
                ? Files.readString(p)
                : "아직 실행 로그가 없습니다.";

        return Map.of(
                "job", j,
                "log", text.substring(
                        Math.max(0, text.length() - 64000)
                )
        );
    }

    // ============================================================
    // 검출 상세 정보 및 수동 검수
    // ============================================================

    @GetMapping("/results/{id}/details")
    public Map<String, Object> details(@PathVariable String id) {
        return Map.of(
                "candidates", candidates.findByResultId(id)
                        .stream()
                        .map(c -> f.object(c.payload))
                        .toList(),
                "faces", faces.findByResultId(id)
                        .stream()
                        .map(c -> f.object(c.payload))
                        .toList()
        );
    }

    @PutMapping("/results/{id}/review")
    @Transactional
    public Review review(
            @PathVariable String id,
            @RequestBody Map<String, Object> body
    ) {
        results.findById(id).orElseThrow();

        Review r = reviews.findByResultId(id)
                .orElseGet(Review::new);

        if (r.id == null) {
            r.id = FilesService.id();
        }

        r.resultId = id;

        r.missingFaces = (
                (Number) body.getOrDefault("missingFaces", 0)
        ).intValue();

        r.falseFaces = (
                (Number) body.getOrDefault("falseFaces", 0)
        ).intValue();

        if (r.missingFaces < 0
                || r.falseFaces < 0
                || r.missingFaces > 10000
                || r.falseFaces > 10000) {
            throw new IllegalArgumentException("검수 개수 범위 오류");
        }

        r.quality = String.valueOf(
                body.getOrDefault("quality", "추가 확인")
        );

        r.note = String.valueOf(
                body.getOrDefault("note", "")
        );

        if (r.note.length() > 4000 || r.quality.length() > 200) {
            throw new IllegalArgumentException("검수 내용이 너무 깁니다.");
        }

        r.done = Boolean.TRUE.equals(body.get("done"));
        r.updatedAt = FilesService.now();

        return reviews.save(r);
    }

    // ============================================================
    // 보고서 파일 목록 및 이미지 조회
    // ============================================================

    @GetMapping("/reports/{id}/files")
    public List<Artifact> files(@PathVariable String id) {
        reports.findById(id).orElseThrow();

        return artifacts.findByReportId(id);
    }

    @GetMapping("/images/original/{id}")
    public ResponseEntity<Resource> original(
            @PathVariable String id
    ) throws Exception {

        DsImage image = images.findById(id).orElseThrow();

        return serve(
                f.safe(
                        "datasets/" + image.datasetId
                                + "/data/images/" + image.filename
                ),
                image.filename,
                false
        );
    }

    @GetMapping("/images/result/{id}")
    public ResponseEntity<Resource> result(
            @PathVariable String id
    ) throws Exception {

        Result r = results.findById(id).orElseThrow();

        if (r.imagePath == null || r.imagePath.isBlank()) {
            throw new IllegalArgumentException("결과 이미지가 없습니다.");
        }

        return serve(
                f.safe(r.imagePath),
                r.filename,
                false
        );
    }

    // ============================================================
    // 산출물 및 보고서 ZIP 다운로드
    // ============================================================

    @GetMapping("/artifacts/{id}")
    public ResponseEntity<Resource> artifact(
            @PathVariable String id
    ) throws Exception {

        Artifact a = artifacts.findById(id).orElseThrow();
        Report report = reports.findById(a.reportId).orElseThrow();

        Path p = f.safe(report.rootPath + "/" + a.path);

        if (!f.sha(p).equals(a.sha256)) {
            throw new IllegalArgumentException("파일 무결성 검증 실패");
        }

        return serve(
                p,
                p.getFileName().toString(),
                true
        );
    }

    @GetMapping("/reports/{id}/zip")
    public ResponseEntity<
            org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody
            > zip(@PathVariable String id) throws Exception {

        Report report = reports.findById(id).orElseThrow();
        Path base = f.safe(report.rootPath);

        List<Map<String, Object>> manifest = f.list(
                Files.readString(base.resolve("manifest.json"))
        );

        f.verify(base, manifest);

        org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody data =
                out -> {
                    try (ZipOutputStream z = new ZipOutputStream(
                            out,
                            java.nio.charset.StandardCharsets.UTF_8
                    )) {
                        for (var item : manifest) {
                            String n = item.get("path").toString();

                            z.putNextEntry(new ZipEntry(n));
                            Files.copy(base.resolve(n), z);
                            z.closeEntry();
                        }

                        z.putNextEntry(new ZipEntry("manifest.json"));

                        Files.copy(
                                base.resolve("manifest.json"),
                                z
                        );

                        z.closeEntry();
                    }
                };

        return ResponseEntity.ok()
                .header(
                        HttpHeaders.CONTENT_DISPOSITION,
                        "attachment; filename=\""
                                + report.runId
                                + "-r"
                                + report.revision
                                + ".zip\""
                )
                .contentType(MediaType.parseMediaType("application/zip"))
                .body(data);
    }

    // ============================================================
    // 공통 파일 응답 처리
    // ============================================================

    private ResponseEntity<Resource> serve(
            Path p,
            String name,
            boolean download
    ) throws Exception {

        if (!Files.isRegularFile(p)) {
            throw new java.io.FileNotFoundException("파일 없음");
        }

        String type = Files.probeContentType(p);

        if (type == null) {
            type = "application/octet-stream";
        }

        var disposition = download
                ? ContentDisposition.attachment()
                : ContentDisposition.inline();

        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType(type))
                .header(
                        HttpHeaders.CONTENT_DISPOSITION,
                        disposition.filename(
                                name,
                                java.nio.charset.StandardCharsets.UTF_8
                        ).build().toString()
                )
                .header("X-Content-Type-Options", "nosniff")
                .body(new FileSystemResource(p));
    }
}