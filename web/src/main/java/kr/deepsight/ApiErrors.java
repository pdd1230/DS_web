package kr.deepsight;

import org.springframework.web.bind.annotation.*;
import org.springframework.http.*;

import java.util.*;

@RestControllerAdvice
@RequestMapping("/api")
public class ApiErrors {

    // API 처리 중 발생한 예외를 HTTP 상태 코드와 오류 메시지로 반환합니다.
    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, Object>> handle(Exception e) {

        int code =
                e instanceof NoSuchElementException
                        || e instanceof java.io.FileNotFoundException
                        ? 404
                        : e instanceof IllegalArgumentException
                        ? 400
                        : 500;

        return ResponseEntity.status(code)
                .body(
                        Map.of(
                                "error",
                                JobPoller.shortError(e)
                        )
                );
    }
}