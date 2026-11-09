package kr.deepsight;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import java.net.*;import java.net.http.*;import java.time.Duration;import java.util.*;
@Component
public class PythonClient {
 private final String base,key;private final FilesService f;
 private final HttpClient client=HttpClient.newBuilder().version(HttpClient.Version.HTTP_1_1).connectTimeout(Duration.ofSeconds(4)).build();
 public PythonClient(@Value("${ds.python}")String base,@Value("${ds.key}")String key,FilesService f){this.base=base;this.key=key;this.f=f;}
 public Map<String,Object> request(String path,Object payload)throws Exception{
  HttpRequest.Builder b=HttpRequest.newBuilder(URI.create(base+path)).timeout(Duration.ofSeconds(30)).header("X-DS-Key",key);
  if(payload==null)b.GET();else b.header("Content-Type","application/json").POST(HttpRequest.BodyPublishers.ofString(f.encode(payload)));
  var response=client.send(b.build(),HttpResponse.BodyHandlers.ofString());
  if(response.statusCode()>=400&&response.statusCode()<500)throw new IllegalArgumentException("Python 요청 거절 "+response.statusCode()+": "+response.body());
  if(response.statusCode()>=400)throw new IllegalStateException("Python HTTP "+response.statusCode()+": "+response.body());
  return f.object(response.body());
 }
}
