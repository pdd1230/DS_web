package kr.deepsight;

import org.springframework.stereotype.Component;
import org.springframework.scheduling.annotation.Scheduled;

import kr.deepsight.Models.*;

import java.util.*;

@Component
public class JobPoller {

    final Jobs jobs;
    final Runs runs;
    final FilesService f;
    final PythonClient python;
    final ReportImporter importer;

    public JobPoller(
            Jobs j,
            Runs r,
            FilesService f,
            PythonClient p,
            ReportImporter i
    ) {
        jobs = j;
        runs = r;
        this.f = f;
        python = p;
        importer = i;
    }

    // 이전 실행이 끝난 뒤 2초 후에 다시 실행합니다.
    @Scheduled(fixedDelay = 2000)
    public synchronized void tick() {

        for (Job j : jobs.findByStatusIn(
                List.of("QUEUED", "RUNNING")
        )) {
            Run r = runs.findById(j.runId).orElseThrow();

            try {
                Map<String, Object> answer;

                // ============================================
                // 1. 대기 중인 작업을 Python에 제출
                // ============================================

                if (j.status.equals("QUEUED")) {
                    answer = python.request(
                            "/jobs",
                            Map.of(
                                    "jobId", j.id,
                                    "runId", r.id,
                                    "kind", j.kind,
                                    "revision", j.revision,
                                    "settings", f.object(r.settingsJson)
                            )
                    );

                    j.status = "RUNNING";
                    r.status = "RUNNING";

                    runs.save(r);
                    jobs.save(j);
                }

                // ============================================
                // 2. Python에서 작업 상태 및 진행률 조회
                // ============================================

                answer = python.request(
                        "/jobs/" + j.id,
                        null
                );

                j.progress = (
                        (Number) answer.getOrDefault("progress", 0)
                ).intValue();

                j.error = "";

                String status = answer.get("status").toString();

                // ============================================
                // 3. 완료한 작업의 결과를 DB로 수집
                // ============================================

                if (status.equals("COMPLETED")) {
                    r.status = "IMPORTING";
                    runs.save(r);

                    try {
                        importer.accept(
                                j.id,
                                answer.get("report").toString()
                        );

                    } catch (Exception e) {
                        j.status = "IMPORT_FAILED";
                        j.error = shortError(e);

                        jobs.save(j);

                        r.status = "IMPORT_FAILED";
                        r.error = j.error;

                        runs.save(r);
                    }

                    // ============================================
                    // 4. Python에서 실패한 작업 처리
                    // ============================================

                } else if (status.equals("FAILED")) {
                    j.status = "FAILED";
                    j.error = String.valueOf(answer.get("error"));

                    jobs.save(j);

                    r.status = "FAILED";
                    r.error = j.error;

                    runs.save(r);

                } else {
                    // 실행 중인 작업의 진행률 등을 저장합니다.
                    jobs.save(j);
                }

            } catch (Exception e) {
                // ============================================
                // 5. 요청 오류 및 연결·처리 시간 초과 처리
                // ============================================

                j.error = shortError(e);

                // 일시적인 연결 오류는 재시도할 수 있도록 상태를 유지합니다.
                // 요청 검증 오류이거나 작업 생성 후 2시간이 지나면 실패 처리합니다.
                if (e instanceof IllegalArgumentException
                        || java.time.Duration.between(
                        java.time.OffsetDateTime.parse(j.createdAt),
                        java.time.OffsetDateTime.now()
                ).toHours() >= 2) {

                    j.status = "FAILED";
                    r.status = "FAILED";

                    r.error = (
                            e instanceof IllegalArgumentException
                                    ? "요청 검증 실패: "
                                    : "연결/처리 제한 시간 초과: "
                    ) + j.error;

                    runs.save(r);
                }

                jobs.save(j);
            }
        }
    }

    // 오류 메시지를 최대 3,900자로 제한합니다.
    static String shortError(Exception e) {
        String s = e.getMessage() == null
                ? e.toString()
                : e.getMessage();

        return s.substring(
                0,
                Math.min(3900, s.length())
        );
    }
}