package kr.deepsight;

import jakarta.servlet.*;
import jakarta.servlet.http.*;

import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Set;

/**
 * 로컬 전용 애플리케이션에서
 * 다른 웹사이트가 브라우저를 통해 작업을 요청하는 것을 방지합니다.
 */
@Component
public class LocalRequestFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(
            HttpServletRequest req,
            HttpServletResponse res,
            FilterChain chain
    ) throws ServletException, IOException {

        // 조회용 메서드를 제외한 API 요청을 검사합니다.
        if (req.getRequestURI().startsWith("/api/")
                && !Set.of("GET", "HEAD", "OPTIONS")
                .contains(req.getMethod())) {

            String origin = req.getHeader("Origin");
            String site = req.getHeader("Sec-Fetch-Site");

            String expected = req.getScheme()
                    + "://"
                    + req.getHeader("Host");

            // 다른 사이트에서 보낸 요청이면 차단합니다.
            if ("cross-site".equals(site)
                    || (origin != null && !origin.equals(expected))) {

                res.sendError(
                        403,
                        "다른 사이트에서의 실행 요청은 허용하지 않습니다."
                );

                return;
            }
        }

        // 검사를 통과한 요청은 다음 필터 또는 컨트롤러로 전달합니다.
        chain.doFilter(req, res);
    }
}