package kr.deepsight;
import jakarta.persistence.*;
/** Package-private entities keep the teaching project small; DTOs are served via controllers. */
public class Models {
 @Entity(name="DsDataset") @Table(name="dataset") public static class Dataset {
  @Id public String id; public String name; public String parentId; public String createdAt;
  @Column(columnDefinition="LONGTEXT") public String groundTruth;
  public Dataset(){}
 }
 @Entity(name="DsImage") @Table(name="dataset_image",uniqueConstraints=@UniqueConstraint(columnNames={"dataset_id","filename"})) public static class DsImage {
  @Id public String id; public String datasetId; public String filename; public int groundTruth; public String scene;
  @Column(length=2000) public String note; public int width; public int height; public long size;
  public String sha256; public DsImage(){}
 }
 @Entity(name="DsRun") @Table(name="experiment") public static class Run {
  @Id public String id; public String datasetId; public String title; public String kind; public String status; public String createdAt; public String completedAt; public String previousRunId; public String origin;
  @Column(length=4000) public String note;
  @Column(length=4000) public String previousNote;
  @Column(length=4000) public String error;
  @Column(columnDefinition="LONGTEXT") public String settingsJson;
  public int currentRevision; public Run(){}
 }
 @Entity(name="DsJob") @Table(name="experiment_job") public static class Job {
  @Id public String id; public String runId; public String kind; public String status; public int progress; public int revision; public String createdAt;
  @Column(length=4000) public String error; public Job(){}
 }
 @Entity(name="DsResult") @Table(name="image_policy_result",uniqueConstraints=@UniqueConstraint(columnNames={"run_id","filename","policy"})) public static class Result {
  @Id public String id; public String runId; public String filename; public String policy; public int groundTruth;
  public Integer detected; public String evaluation; public String processingStatus; public boolean reviewRequired;
  public String scene; @Column(length=2000) public String note; @Column(length=1000) public String imagePath;
  public Result(){}
 }
 @Entity(name="DsCandidate") @Table(name="detection_candidate") public static class Candidate {
  @Id public String id; public String resultId; @Column(columnDefinition="LONGTEXT") public String payload; public Candidate(){}
 }
 @Entity(name="DsFace") @Table(name="detected_face") public static class Face {
  @Id public String id; public String resultId; @Column(columnDefinition="LONGTEXT") public String payload; public Face(){}
 }
 @Entity(name="DsReview") @Table(name="manual_review",uniqueConstraints=@UniqueConstraint(columnNames="result_id")) public static class Review {
  @Id public String id; public String resultId; public boolean done; public int missingFaces; public int falseFaces;
  public String quality; @Column(length=4000) public String note; public String updatedAt; public Review(){}
 }
 @Entity(name="DsReport") @Table(name="report_revision",uniqueConstraints=@UniqueConstraint(columnNames={"run_id","revision"})) public static class Report {
  @Id public String id; public String runId; public int revision; public String rootPath; public String createdAt;
  @Column(columnDefinition="LONGTEXT") public String summaryJson;
  @Column(columnDefinition="LONGTEXT") public String reviewSnapshot;
  public Report(){}
 }
 @Entity(name="DsArtifact") @Table(name="artifact",uniqueConstraints=@UniqueConstraint(columnNames={"report_id","path"})) public static class Artifact {
  @Id public String id; public String reportId; @Column(length=500) public String path; public long size; public String sha256; public Artifact(){}
 }
}
