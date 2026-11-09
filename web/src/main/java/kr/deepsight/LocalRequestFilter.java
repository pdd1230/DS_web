package kr.deepsight;
import jakarta.servlet.*;import jakarta.servlet.http.*;import org.springframework.stereotype.Component;import org.springframework.web.filter.OncePerRequestFilter;import java.io.IOException;import java.util.Set;
/** Local-only app: prevent other websites from submitting work through the browser. */
@Component public class LocalRequestFilter extends OncePerRequestFilter {
 @Override protected void doFilterInternal(HttpServletRequest req,HttpServletResponse res,FilterChain chain)throws ServletException,IOException{
  if(req.getRequestURI().startsWith("/api/")&&!Set.of("GET","HEAD","OPTIONS").contains(req.getMethod())){
   String origin=req.getHeader("Origin"),site=req.getHeader("Sec-Fetch-Site");String expected=req.getScheme()+"://"+req.getHeader("Host");
   if("cross-site".equals(site)||(origin!=null&&!origin.equals(expected))){res.sendError(403,"다른 사이트에서의 실행 요청은 허용하지 않습니다.");return;}
  }chain.doFilter(req,res);
 }
}
