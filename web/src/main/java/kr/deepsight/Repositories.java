package kr.deepsight;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.*;

import kr.deepsight.Models.*;

// ============================================================
// 데이터셋 저장소
// ============================================================

interface Datasets extends JpaRepository<Dataset, String> {

    // 생성 시각이 최신인 데이터셋부터 조회합니다.
    List<Dataset> findAllByOrderByCreatedAtDesc();
}

// ============================================================
// 데이터셋 사진 저장소
// ============================================================

interface Images extends JpaRepository<DsImage, String> {

    // 특정 데이터셋의 사진을 파일명순으로 조회합니다.
    List<DsImage> findByDatasetIdOrderByFilename(String id);
}

// ============================================================
// 실험 저장소
// ============================================================

interface Runs extends JpaRepository<Run, String> {

    // 생성 시각이 최신인 실험부터 조회합니다.
    List<Run> findAllByOrderByCreatedAtDesc();
}

// ============================================================
// 실험 작업 저장소
// ============================================================

interface Jobs extends JpaRepository<Job, String> {

    // 특정 실험의 작업을 생성 시각 내림차순으로 조회합니다.
    List<Job> findByRunIdOrderByCreatedAtDesc(String id);

    // 지정한 상태 중 하나에 해당하는 작업을 조회합니다.
    List<Job> findByStatusIn(Collection<String> statuses);
}

// ============================================================
// 사진별·정책별 분석 결과 저장소
// ============================================================

interface Results extends JpaRepository<Result, String> {

    // 특정 실험의 결과를 파일명·정책 오름차순으로 조회합니다.
    List<Result> findByRunIdOrderByFilenameAscPolicyAsc(String id);

    // 실험 ID·파일명·정책이 일치하는 결과를 조회합니다.
    Optional<Result> findByRunIdAndFilenameAndPolicy(
            String runId,
            String filename,
            String policy
    );
}

// ============================================================
// 검출 후보 저장소
// ============================================================

interface Candidates extends JpaRepository<Candidate, String> {

    List<Candidate> findByResultId(String id);
}

// ============================================================
// 검출된 얼굴 저장소
// ============================================================

interface Faces extends JpaRepository<Face, String> {

    List<Face> findByResultId(String id);
}

// ============================================================
// 수동 검수 저장소
// ============================================================

interface Reviews extends JpaRepository<Review, String> {

    Optional<Review> findByResultId(String id);
}

// ============================================================
// 보고서 개정 이력 저장소
// ============================================================

interface Reports extends JpaRepository<Report, String> {

    // 특정 실험의 보고서를 최신 개정부터 조회합니다.
    List<Report> findByRunIdOrderByRevisionDesc(String id);

    // 특정 실험의 지정한 개정 보고서를 조회합니다.
    Optional<Report> findByRunIdAndRevision(
            String id,
            int revision
    );
}

// ============================================================
// 보고서 산출물 저장소
// ============================================================

interface Artifacts extends JpaRepository<Artifact, String> {

    List<Artifact> findByReportId(String id);
}