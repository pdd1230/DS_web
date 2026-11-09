package kr.deepsight;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import tools.jackson.databind.json.JsonMapper;
import java.nio.file.*;
import java.io.*;
import java.security.*;
import java.util.*;
@Component
public class FilesService {
 public final Path home,storage;
 public final JsonMapper json=JsonMapper.builder().build();
 public FilesService(@Value("${ds.home}")String home,@Value("${ds.storage}")String storage)throws IOException{
  this.home=Path.of(home).toAbsolutePath().normalize();this.storage=Path.of(storage).toAbsolutePath().normalize();Files.createDirectories(this.storage);
 }
 public Path safe(String relative){Path p=storage.resolve(relative).normalize();if(!p.startsWith(storage))throw new IllegalArgumentException("저장소 밖 경로입니다.");return p;}
 public static String id(){return UUID.randomUUID().toString();}
 public static String now(){return java.time.OffsetDateTime.now(java.time.ZoneId.of("Asia/Seoul")).toString();}
 public String encode(Object value){return json.writeValueAsString(value);}
 @SuppressWarnings("unchecked") public Map<String,Object> object(String value){return json.readValue(value,Map.class);}
 @SuppressWarnings("unchecked") public List<Map<String,Object>> list(String value){return json.readValue(value,List.class);}
 public void writeJson(Path p,Object v)throws IOException{Files.createDirectories(p.getParent());Path temp=p.resolveSibling(p.getFileName()+".tmp");Files.writeString(temp,encode(v));Files.move(temp,p,StandardCopyOption.REPLACE_EXISTING);}
 public void copyTree(Path from,Path to)throws IOException{if(!Files.isDirectory(from))throw new IOException("폴더 없음: "+from);try(var paths=Files.walk(from)){for(Path source:paths.toList()){if(Files.isSymbolicLink(source))throw new IOException("심볼릭 링크 허용 안 함");Path dest=to.resolve(from.relativize(source));if(Files.isDirectory(source))Files.createDirectories(dest);else {Files.createDirectories(dest.getParent());Files.copy(source,dest);}}}}
 public String sha(Path p)throws IOException{try{MessageDigest d=MessageDigest.getInstance("SHA-256");try(InputStream in=Files.newInputStream(p)){byte[] b=new byte[65536];for(int n;(n=in.read(b))!=-1;)d.update(b,0,n);}return HexFormat.of().formatHex(d.digest());}catch(NoSuchAlgorithmException e){throw new IllegalStateException(e);}}
 public List<Map<String,Object>> manifest(Path folder)throws IOException{List<Map<String,Object>> list=new ArrayList<>();try(var files=Files.walk(folder)){for(Path p:files.filter(Files::isRegularFile).sorted().toList())list.add(Map.of("path",folder.relativize(p).toString().replace('\\','/'),"size",Files.size(p),"sha256",sha(p)));}return list;}
 public void verify(Path base,List<Map<String,Object>> entries)throws IOException{for(var e:entries){Path p=base.resolve(e.get("path").toString()).normalize();if(!p.startsWith(base.normalize())||!Files.isRegularFile(p)||Files.size(p)!=((Number)e.get("size")).longValue()||!sha(p).equals(e.get("sha256")))throw new IOException("파일 무결성 검증 실패: "+e.get("path"));}}
 public static String filename(String n){if(n==null||n.isBlank()||n.length()>180||n.contains("/")||n.contains("\\")||n.contains(":")||n.contains("\u0000")||n.equals(".")||n.equals(".."))throw new IllegalArgumentException("올바른 파일명이 아닙니다.");return n;}
}
