package kr.deepsight;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import kr.deepsight.Models.*;

import java.nio.file.*;
import java.util.*;

@Service
public class DatasetService {

    final Datasets datasets;
    final Images images;
    final FilesService f;
    final PythonClient python;

    public DatasetService(
            Datasets d,
            Images i,
            FilesService f,
            PythonClient p
    ) {
        datasets = d;
        images = i;
        this.f = f;
        python = p;
    }

    @Transactional
    public synchronized Dataset create(
            String name,
            String gt,
            List<MultipartFile> photos,
            String parent,
            boolean sample
    ) throws Exception {

        // ====================================================
        // 1. 데이터셋 이름 검사
        // ====================================================

        if (name == null || name.isBlank() || name.length() > 200) {
            throw new IllegalArgumentException(
                    "데이터셋 이름은 1~200자입니다."
            );
        }

        // ====================================================
        // 2. 데이터셋 ID 발급 및 사진 저장 폴더 생성
        // ====================================================

        String id = FilesService.id();

        Path data = f.safe(
                "datasets/" + id + "/data"
        );

        Files.createDirectories(data.resolve("images"));

        // ====================================================
        // 3. 등록 방식에 따라 사진 준비
        // ====================================================

        if (sample) {
            // 첨부 기준 사진과 정답표를 복사합니다.
            f.copyTree(
                    f.home.resolve("legacy/data/images"),
                    data.resolve("images")
            );

            gt = Files.readString(
                    f.home.resolve("legacy/data/ground_truth.csv")
            );

        } else if (parent != null && !parent.isBlank()) {
            // 기존 데이터셋의 사진을 복사합니다.
            datasets.findById(parent).orElseThrow();

            f.copyTree(
                    f.safe(
                            "datasets/" + parent + "/data/images"
                    ),
                    data.resolve("images")
            );

        } else {
            // 새로 업로드한 사진을 검사하고 저장합니다.
            if (photos == null
                    || photos.isEmpty()
                    || photos.size() > 200) {
                throw new IllegalArgumentException(
                        "사진 1~200장을 선택하세요."
                );
            }

            Set<String> names = new HashSet<>();

            for (MultipartFile photo : photos) {
                String n = FilesService.filename(
                        photo.getOriginalFilename()
                );

                if (photo.getSize() > 25L * 1024 * 1024
                        || photo.isEmpty()) {
                    throw new IllegalArgumentException(
                            "사진 크기는 1바이트~25MB입니다."
                    );
                }

                if (!names.add(n.toLowerCase(Locale.ROOT))) {
                    throw new IllegalArgumentException(
                            "파일명 중복: " + n
                    );
                }

                try (var in = photo.getInputStream()) {
                    Files.copy(
                            in,
                            data.resolve("images").resolve(n)
                    );
                }
            }
        }

        // ====================================================
        // 4. 정답표 검사 및 파일 저장
        // ====================================================

        if (gt == null || gt.isBlank() || gt.length() > 1_000_000) {
            throw new IllegalArgumentException(
                    "정답표가 비어 있거나 너무 큽니다."
            );
        }

        Files.writeString(
                data.resolve("ground_truth.csv"),
                gt
        );

        // ====================================================
        // 5. Python 서비스에 사진·정답표 검증 요청
        // ====================================================

        var validated = python.request(
                "/datasets/validate",
                Map.of("datasetId", id)
        );

        // ====================================================
        // 6. 데이터셋 정보 DB 저장
        // ====================================================

        Dataset d = new Dataset();

        d.id = id;
        d.name = name;
        d.parentId = parent;
        d.groundTruth = gt;
        d.createdAt = FilesService.now();

        datasets.save(d);

        // ====================================================
        // 7. 검증된 개별 사진 정보 DB 저장
        // ====================================================

        for (Object obj : (List<?>) validated.get("images")) {
            var row = (Map<?, ?>) obj;

            DsImage im = new DsImage();

            im.id = FilesService.id();
            im.datasetId = id;
            im.filename = row.get("filename").toString();

            im.groundTruth = (
                    (Number) row.get("groundTruth")
            ).intValue();

            im.width = (
                    (Number) row.get("width")
            ).intValue();

            im.height = (
                    (Number) row.get("height")
            ).intValue();

            im.size = (
                    (Number) row.get("size")
            ).longValue();

            im.sha256 = row.get("sha256").toString();
            im.scene = row.get("scene").toString();
            im.note = row.get("note").toString();

            images.save(im);
        }

        // ====================================================
        // 8. 파일 무결성 확인용 목록 저장
        // ====================================================

        f.writeJson(
                data.getParent().resolve("manifest.json"),
                f.manifest(data)
        );

        return d;
    }
}