package kr.deepsight;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.*;
import kr.deepsight.Models.*;
interface Datasets extends JpaRepository<Dataset,String>{List<Dataset> findAllByOrderByCreatedAtDesc();}
interface Images extends JpaRepository<DsImage,String>{List<DsImage> findByDatasetIdOrderByFilename(String id);}
interface Runs extends JpaRepository<Run,String>{List<Run> findAllByOrderByCreatedAtDesc();}
interface Jobs extends JpaRepository<Job,String>{List<Job> findByRunIdOrderByCreatedAtDesc(String id);List<Job> findByStatusIn(Collection<String> statuses);}
interface Results extends JpaRepository<Result,String>{List<Result> findByRunIdOrderByFilenameAscPolicyAsc(String id);Optional<Result> findByRunIdAndFilenameAndPolicy(String runId,String filename,String policy);}
interface Candidates extends JpaRepository<Candidate,String>{List<Candidate> findByResultId(String id);}
interface Faces extends JpaRepository<Face,String>{List<Face> findByResultId(String id);}
interface Reviews extends JpaRepository<Review,String>{Optional<Review> findByResultId(String id);}
interface Reports extends JpaRepository<Report,String>{List<Report> findByRunIdOrderByRevisionDesc(String id);Optional<Report> findByRunIdAndRevision(String id,int revision);}
interface Artifacts extends JpaRepository<Artifact,String>{List<Artifact> findByReportId(String id);}
