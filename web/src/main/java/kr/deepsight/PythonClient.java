package kr.deepsight;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.net.*;
import java.net.http.*;
import java.time.Duration;
import java.util.*;

@Component
public class PythonClient {

    private final String base;
    private final String key;
    private final FilesService f;

    // 연결 제한 시간: 4초
    private final HttpClient client = HttpClient.newBuilder()
            .version(HttpClient.Version.HTTP_1_1)
            .connectTimeout(Duration.ofSeconds(4))
            .build();

    public PythonClient(
            @Value("${ds.python}") String base,
            @Value("${ds.key}") String key,
            FilesService f
    ) {
        this.base = base;
        this.key = key;
        this.f = f;
    }

    public Map<String, Object> request(
            String path,
            Object payload
    ) throws Exception {

        // ====================================================
        // 1. 요청 주소·제한 시간·인증 헤더 설정
        // ====================================================

        HttpRequest.Builder b = HttpRequest.newBuilder(
                        URI.create(base + path)
                )
                .timeout(Duration.ofSeconds(30))
                .header("X-DS-Key", key);

        // ====================================================
        // 2. 본문이 없으면 GET, 있으면 JSON POST 요청
        // ====================================================

        if (payload == null) {
            b.GET();
        } else {
            b.header("Content-Type", "application/json")
                    .POST(
                            HttpRequest.BodyPublishers.ofString(
                                    f.encode(payload)
                            )
                    );
        }

        // ====================================================
        // 3. Python 서비스에 요청 전송
        // ====================================================

        var response = client.send(
                b.build(),
                HttpResponse.BodyHandlers.ofString()
        );

        // ====================================================
        // 4. HTTP 오류 응답 검사
        // ====================================================

        if (response.statusCode() >= 400
                && response.statusCode() < 500) {
            throw new IllegalArgumentException(
                    "Python 요청 거절 "
                            + response.statusCode()
                            + ": "
                            + response.body()
            );
        }

        if (response.statusCode() >= 400) {
            throw new IllegalStateException(
                    "Python HTTP "
                            + response.statusCode()
                            + ": "
                            + response.body()
            );
        }

        // ====================================================
        // 5. JSON 응답을 Map으로 변환하여 반환
        // ====================================================

        return f.object(response.body());
    }
}