package kr.deepsight;

import org.springframework.web.bind.annotation.*;
import org.springframework.http.*;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

import java.nio.file.*;
import java.util.*;
import java.util.zip.*;

/**
 * 과거 CLI 백업 자료를 조회합니다.
 * 당시 입력과 설정이 불명확한 자료를 새 실험으로 취급하지 않습니다.
 */
@RestController
@RequestMapping("/api/legacy/backups")
public class LegacyArchiveController {

    private final FilesService f;

    public LegacyArchiveController(FilesService f) {
        this.f = f;
    }

    // ============================================================
    // 백업 ID 및 폴더 검사
    // ============================================================

    private Path folder(String id) {
        if (!id.matches("[A-Za-z0-9_-]{1,80}")) {
            throw new IllegalArgumentException("백업 ID 오류");
        }

        Path root = f.home.resolve("legacy/csv_backup")
                .normalize();

        Path p = root.resolve(id).normalize();

        if (!p.startsWith(root)
                || !Files.isDirectory(p)
                || Files.isSymbolicLink(p)) {
            throw new NoSuchElementException("백업 없음");
        }

        return p;
    }

    // ============================================================
    // 기존 CLI 백업 목록 조회
    // ============================================================

    @GetMapping
    public List<Map<String, Object>> list() throws Exception {
        Path base = f.home.resolve("legacy/csv_backup");

        if (!Files.isDirectory(base)) {
            return List.of();
        }

        List<Map<String, Object>> out = new ArrayList<>();

        try (var paths = Files.list(base)) {
            for (Path p : paths
                    .filter(Files::isDirectory)
                    .sorted(Comparator.reverseOrder())
                    .toList()) {

                String name = p.getFileName().toString();

                if (!name.matches("[A-Za-z0-9_-]{1,80}")) {
                    continue;
                }

                Path note = p.resolve("experiment_note.md");

                out.add(
                        Map.of(
                                "id", name,
                                "note", Files.exists(note)
                                        ? Files.readString(note)
                                        : "설명 없음",
                                "origin", "과거 CLI 백업 · 당시 입력/설정 확인 필요"
                        )
                );
            }
        }

        return out;
    }

    // ============================================================
    // 무결성 검증 후 백업 ZIP 다운로드
    // ============================================================

    @GetMapping("/{id}/zip")
    public ResponseEntity<StreamingResponseBody> zip(
            @PathVariable String id
    ) throws Exception {

        Path base = folder(id);
        Path manifest = base.resolve("backup_manifest.json");

        if (!Files.isRegularFile(manifest)) {
            throw new IllegalArgumentException(
                    "백업 매니페스트 없음"
            );
        }

        // 저장된 파일 목록으로 과거 결과의 무결성을 검증합니다.
        var saved = f.object(
                Files.readString(manifest)
        );

        List<Map<String, Object>> entries = f.list(
                f.encode(saved.get("files"))
        );

        f.verify(
                base.resolve("outputs_snapshot"),
                entries
        );

        // 백업 폴더 전체를 ZIP 스트림으로 전송합니다.
        var all = f.manifest(base);

        StreamingResponseBody body = out -> {
            try (var z = new ZipOutputStream(
                    out,
                    java.nio.charset.StandardCharsets.UTF_8
            )) {
                for (var e : all) {
                    Path p = base.resolve(
                            e.get("path").toString()
                    );

                    if (Files.isSymbolicLink(p)) {
                        throw new java.io.IOException(
                                "링크 파일 허용 안 함"
                        );
                    }

                    z.putNextEntry(
                            new ZipEntry(
                                    e.get("path").toString()
                            )
                    );

                    Files.copy(p, z);
                    z.closeEntry();
                }
            }
        };

        return ResponseEntity.ok()
                .contentType(
                        MediaType.parseMediaType("application/zip")
                )
                .header(
                        HttpHeaders.CONTENT_DISPOSITION,
                        "attachment; filename=\"backup-" + id + ".zip\""
                )
                .body(body);
    }
}