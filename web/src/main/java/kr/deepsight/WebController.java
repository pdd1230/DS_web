package kr.deepsight;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class WebController {

    // 첫 화면 요청을 index 템플릿으로 연결합니다.
    @GetMapping("/")
    public String index() {
        return "index";
    }
}