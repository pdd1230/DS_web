package kr.deepsight;
import org.springframework.web.bind.annotation.*;import org.springframework.http.*;import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;
import java.nio.file.*;import java.util.*;import java.util.zip.*;
/** Inspect old CLI snapshots without treating unknown inputs/settings as a new experiment. */
@RestController @RequestMapping("/api/legacy/backups")
public class LegacyArchiveController {
 private final FilesService f;
 public LegacyArchiveController(FilesService f){this.f=f;}
 private Path folder(String id){if(!id.matches("[A-Za-z0-9_-]{1,80}"))throw new IllegalArgumentException("백업 ID 오류");Path root=f.home.resolve("legacy/csv_backup").normalize(),p=root.resolve(id).normalize();if(!p.startsWith(root)||!Files.isDirectory(p)||Files.isSymbolicLink(p))throw new NoSuchElementException("백업 없음");return p;}
 @GetMapping public List<Map<String,Object>> list()throws Exception{Path base=f.home.resolve("legacy/csv_backup");if(!Files.isDirectory(base))return List.of();List<Map<String,Object>> out=new ArrayList<>();try(var paths=Files.list(base)){for(Path p:paths.filter(Files::isDirectory).sorted(Comparator.reverseOrder()).toList()){String name=p.getFileName().toString();if(!name.matches("[A-Za-z0-9_-]{1,80}"))continue;Path note=p.resolve("experiment_note.md");out.add(Map.of("id",name,"note",Files.exists(note)?Files.readString(note):"설명 없음","origin","과거 CLI 백업 · 당시 입력/설정 확인 필요"));}}return out;}
 @GetMapping("/{id}/zip") public ResponseEntity<StreamingResponseBody> zip(@PathVariable String id)throws Exception{
  Path base=folder(id);Path manifest=base.resolve("backup_manifest.json");if(!Files.isRegularFile(manifest))throw new IllegalArgumentException("백업 매니페스트 없음");var saved=f.object(Files.readString(manifest));List<Map<String,Object>> entries=f.list(f.encode(saved.get("files")));f.verify(base.resolve("outputs_snapshot"),entries);
  var all=f.manifest(base);StreamingResponseBody body=out->{try(var z=new ZipOutputStream(out,java.nio.charset.StandardCharsets.UTF_8)){for(var e:all){Path p=base.resolve(e.get("path").toString());if(Files.isSymbolicLink(p))throw new java.io.IOException("링크 파일 허용 안 함");z.putNextEntry(new ZipEntry(e.get("path").toString()));Files.copy(p,z);z.closeEntry();}}};return ResponseEntity.ok().contentType(MediaType.parseMediaType("application/zip")).header(HttpHeaders.CONTENT_DISPOSITION,"attachment; filename=\"backup-"+id+".zip\"").body(body);
 }
}
