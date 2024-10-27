package artisynth.istar.Mel;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;

import artisynth.core.mechmodels.MechModel;
import artisynth.core.mechmodels.RigidBody;
import artisynth.istar.reconstruction.ComputeUtils;
import artisynth.istar.reconstruction.PolylineSimplifier;
import artisynth.istar.reconstruction.TaskFrame;
import artisynth.istar.reconstruction.MeshManager;

import maspack.matrix.Vector3d;
import maspack.matrix.VectorNd;
import maspack.matrix.Point3d;
import maspack.matrix.RotationMatrix3d;
import maspack.matrix.RigidTransform3d;
import maspack.matrix.NumericalException;
import maspack.matrix.Plane;
import maspack.geometry.BVFeatureQuery;
import maspack.geometry.MeshBase;
import maspack.geometry.MeshFactory;
import maspack.geometry.OBB;
import maspack.geometry.PolygonalMesh;
import maspack.geometry.PolylineMesh;
import maspack.geometry.Vertex3d;
import maspack.geometry.io.GenericMeshReader;
import maspack.geometry.io.GenericMeshWriter;
import maspack.interpolation.CubicHermiteSpline3d;
import maspack.interpolation.Interpolation.Order;
import maspack.interpolation.NumericList;
import maspack.collision.IntersectionContour;
import maspack.collision.SurfaceMeshIntersector;

public class GenerateVSP {
   private static double INF = Double.POSITIVE_INFINITY;
   protected double DENSITY = 1000.0;
   public static int DEFAULT_NUM_PLATE_CURVE_SEGS = 500;

   MechModel myMech;
   MeshManager myMeshManager;
   
   private class FibulaDonorSegment{
      RigidTransform3d myTPS0;  // transform from cut plane 0 to the segment
      RigidTransform3d myTPS1;  // transform from cut plane 1 to the segment
      RigidTransform3d myTSW_M; // segment-to-world transform, in mandible space
      RigidTransform3d myTSW_D; // segment-to-world transform, in donor space
      
      public FibulaDonorSegment() {
         myTPS0 = new RigidTransform3d();
         myTPS1 = new RigidTransform3d();
         myTSW_M = new RigidTransform3d();
         myTSW_D = new RigidTransform3d();
      }
   }
   
   public GenerateVSP() {
      
   }
   
   public void build(String[] args) {
      
   }
   
   //CONSTRUCT Java Objects from Python Data 
   public Vector3d setVector3d(float x, float y, float z) {
      Vector3d vector3d = new Vector3d(Double.valueOf (x), Double.valueOf (y), Double.valueOf (z));
      return vector3d;
   }
   
   public RotationMatrix3d setRotation3d(float m00, float m01, float m02, 
                                         float m10, float m11, float m12,
                                         float m20, float m21, float m22) {
      RotationMatrix3d rotation3d = new RotationMatrix3d(
                                    Double.valueOf (m00), Double.valueOf (m01), Double.valueOf (m02),
                                    Double.valueOf (m10), Double.valueOf(m11), Double.valueOf (m12),
                                    Double.valueOf (m20), Double.valueOf (m21), Double.valueOf (m22));
      return rotation3d;
   }
   
   public RigidTransform3d setRigidTransform3d(Vector3d p, RotationMatrix3d R) {
      RigidTransform3d rigid3d = new RigidTransform3d(p, R);
      return rigid3d;
   }
   
   public Plane setPlane(Vector3d n, Vector3d p) {
      Plane plane = new Plane(n, p);
      return plane;
   }
   
   public Point3d setPoint3d(float x, float y, float z) {
      Point3d point3d = new Point3d();
      point3d.set (Double.valueOf (x), Double.valueOf (y), Double.valueOf (z));
      return point3d;
   }
   
   public ArrayList<float[]> changeFloatToArrayList (float[][] fids_list){
      ArrayList<float[]> temp = new ArrayList<float[]>(fids_list.length);
      Collections.addAll (temp, fids_list);
      return temp;
   }
   
   public ArrayList<Point3d> setArrayPoint3d(ArrayList<float[]> arr){
      ArrayList<Point3d> arr3d = new ArrayList<Point3d>();
      for (int i = 0; i < arr.size (); i++) {
         Point3d point3d = new Point3d(arr.get(i)[0], arr.get (i)[1], arr.get(i)[2]);
         arr3d.add (point3d);
      }
      return arr3d;
   }
   
//   public ArrayList<Point3d> setArrayListPoint3d(float[][] fids_list){
//      ArrayList<float[]> temp = new ArrayList<float[]>(fids_list.length);
//      Collections.addAll (temp, fids_list);
//      ArrayList<Point3d> arr3d = new ArrayList<Point3d>();
//      for (int i = 0; i < arr3d.size(); i++) {
//         Point3d point3d = new Point3d(temp.get(i)[0], temp.get(i)[1], temp.get(i)[2]);
//         arr3d.add (point3d);
//      }
//      return arr3d; 
//   }
   
   public ArrayList<Double> changeTransformToArray (RigidTransform3d transform){
      RotationMatrix3d rot = transform.R;
      Vector3d trans = transform.p;
      ArrayList<Double> output = new ArrayList<Double>();
      output.add (rot.m00);
      output.add (rot.m01);
      output.add (rot.m02);
      output.add (trans.x);
      
      output.add (rot.m10);
      output.add (rot.m11);
      output.add (rot.m12);
      output.add (trans.y);
      
      output.add (rot.m20);
      output.add (rot.m21);
      output.add (rot.m22);
      output.add (trans.z);
      
      output.add (0.0);
      output.add (0.0);
      output.add (0.0);
      output.add (1.0);
      return output;
   }
   
   /**
    * 
    */
   public PolylineMesh createPlateCurve(ArrayList<Point3d> contour) {
      NumericList numericList = new NumericList(3);
      numericList.setInterpolationOrder (Order.Cubic);
      for (int i=0; i < contour.size (); i++) {
         double s = i/(double)(contour.size()-1);
         numericList.add (contour.get (i), s);
      }
      int nsegs = DEFAULT_NUM_PLATE_CURVE_SEGS;
      ArrayList<Point3d> interpolatedPnts = new ArrayList<>(nsegs+1);
      int[][] indices = new int[1][nsegs+1];
      VectorNd vec3 = new VectorNd(3);
      for (int k=0; k<=nsegs; k++) {
         double s = k/(double)nsegs;
         numericList.interpolate (vec3, s);
         interpolatedPnts.add (new Point3d(vec3));
         indices[0][k] = k;
      }
      if (true) {
        Collections.reverse (interpolatedPnts); 
      }
      PolylineMesh mesh = new PolylineMesh();
      mesh.set (interpolatedPnts.toArray(new Point3d[0]));
      return mesh;
   }
   
   /**
    * Returns true if the direction of the last two points of a point list are
    * heading *into* a plane (i.e., if p0 and p1 are the second-to-last and
    * last points, {@code (p1-p0) . nrm < 0}),
    */
   private boolean headingIntoPlane (ArrayList<Point3d> plist, Plane plane) {
      Vector3d dir = new Vector3d();
      if (plist.size() > 1) {
         int k = plist.size()-1;
         dir.sub (plist.get(k), plist.get(k-1));
         return plane.getNormal().dot(dir) < 0;
      }
      else {
         return false;
      }
   }
   
   public ArrayList<Point3d> computeRDPLine(
      ArrayList<Point3d> contour, Plane planeL, Plane planeR, double minSegLength, int maxSegments){
      double distance = minSegLength;
      int segments = maxSegments;

      PolylineMesh curveMesh = createPlateCurve(contour);
      // find the points in the plate line that are clipped by the resection
      // region, with the end points just outside the region
      boolean insideResectRegion = false;
      ArrayList<Point3d> clippedPlateLine = new ArrayList<>();
      for (int k=0; k<curveMesh.numVertices (); k++) {
         Point3d pos = curveMesh.getVertex (k).getPosition ();
         System.out.println(pos);
         if (!insideResectRegion) {
            if (planeL.distance(pos) >= 0) {
               if (k == 0) {
                  break;        //plate line does not extend beyond resection region
               }
               clippedPlateLine.add (curveMesh.getVertex (k-1).getPosition());
               insideResectRegion = true;
            }
         }
         else {
            clippedPlateLine.add (pos);
            //if (planeR.distance (pos) < 0 && headingIntoPlane(clippedPlateLine, planeR)) {
            if (planeR.distance (pos) < 0 && headingIntoPlane(clippedPlateLine, planeR)) {
               System.out.println("Executed");
               insideResectRegion = false;
               break;
            }
//            if (planeR.distance (pos) < 0) {
//               insideResectRegion = false;
//               break;
//            }
         }
      }

      if (clippedPlateLine.size() == 0 || insideResectRegion) {
         throw new IllegalArgumentException (
            "Plate line does not adequately extend beyond the resection region - test");
      }

      // Create RDP line from the clipped plate line
      ArrayList<Point3d> rdpLine = 
         PolylineSimplifier.bisectSimplifyDouglasPeucker (
            clippedPlateLine, distance, segments);

      // project rdpLine end points onto the resection planes
      Point3d p0 = rdpLine.get(0);
      double d0 = planeL.project (p0, p0);
      Point3d pl = rdpLine.get(rdpLine.size()-1);
      double dl = planeR.project (pl, pl);
      
      return rdpLine;
   }
   
   /**
    * Create the coordinate frames for each donor segment in mandible space,
    * together with the cut plane positions relative to the segment.
  * @throws IOException 
    */
   public ArrayList<FibulaDonorSegment> createSegmentSpecs (
      ArrayList<Point3d> rdpLine, PolygonalMesh mandibleMesh,
      Plane resectPlaneL, Plane resectPlaneR, Boolean leftToRight) throws IOException {

      //PolygonalMesh mandibleMesh = new PolygonalMesh(mandibleFilepath);
      if (!leftToRight) {
         Collections.reverse (rdpLine);
      }

      ArrayList<FibulaDonorSegment> segs = new ArrayList<>();
      // rdpLine gives the end points for the segments
      // compute segment coordinate frames and lengths
      RigidTransform3d TSW_prev = null;
      for (int i=0; i<rdpLine.size()-1; i++) {
         Point3d pos0 = rdpLine.get(i);
         Point3d pos1 = rdpLine.get(i+1);
         FibulaDonorSegment spec = new FibulaDonorSegment();
         RigidTransform3d TSW = computeSegmentFrame (pos0, pos1, mandibleMesh);
         if (TSW_prev != null) {
            alignYZ (TSW, TSW_prev);
         }
         spec.myTSW_M.set (TSW);
         segs.add (spec);
         TSW_prev = TSW;
      }
      // compute segment cut planes based on the resection planes and the RDP
      // line
      for (int i=0; i<segs.size(); i++) {
         Point3d pos0 = rdpLine.get(i);
         Point3d pos1 = rdpLine.get(i+1);
         FibulaDonorSegment spec = segs.get(i);
         RigidTransform3d TSW_M = spec.myTSW_M;
         if (i == 0) {
            // plane 0 is the left resection plane
            spec.myTPS0.set (
               getPlaneTrans (TSW_M, resectPlaneL.getNormal(), pos0));
         }
         else {
            // plane 0 is perpendicular to the average RDP line direction
            // between this segment and the previous one
            Vector3d nrm = averageZDir (TSW_M, segs.get(i-1).myTSW_M);
            nrm.negate();
            spec.myTPS0.set (getPlaneTrans (TSW_M, nrm, pos0));
         }
         if (i == segs.size()-1) {
            // plane 1 is the right resection plane
            spec.myTPS1.set (
               getPlaneTrans (TSW_M, resectPlaneR.getNormal(), pos1));
         }
         else {
            // plane 1 is perpendicular to the average RDP line direction
            // between this segment and the next one
            Vector3d nrm = averageZDir (TSW_M, segs.get(i+1).myTSW_M);
            spec.myTPS1.set (getPlaneTrans (TSW_M, nrm, pos1));
         }
      }
      return segs;
   }
   
   /**
    * 
    */
   public CubicHermiteSpline3d findDonorCenterCurve (
      CubicHermiteSpline3d curve, PolygonalMesh clippedMesh, int npnts) {

      double maxz = -INF;
      double minz =  INF;
      for (Vertex3d vtx : clippedMesh.getVertices()) {
         double z = vtx.pnt.z;
         if (z > maxz) {
            maxz = z;    //max z for clipped mesh vertices
         }
         if (z < minz) {
            minz = z;    //min z for clipped mesh vertices
         }
      }
      double lenz = maxz-minz;
      if (lenz == 0) {
//         return 0;
         return null;
         //return RigidTransform3d.IDENTITY;
      }
      RigidTransform3d TCW = new RigidTransform3d();
      clippedMesh.getMeshToWorld (TCW);
      clippedMesh.setMeshToWorld (RigidTransform3d.IDENTITY); //Temp remove TCW. Should be setMeshToWorld

      PolygonalMesh cutPlane = MeshFactory.createPlane (100, 100, 30, 30);
      ArrayList<Point3d> cpnts = new ArrayList<>();
      RigidTransform3d TPW = new RigidTransform3d(); // cut plane pose wrt world
      double endTol = 0.001;
      double maxr = 0;
      double r = 0;
      //double count = 0;
      for (int i=0; i<=npnts; i++) {
         double z = minz + i*lenz/npnts;
         // shrink cut plane z from the end points to ensure a good
         // intersection
         if (i == 0) {
            TPW.p.z = z + endTol;
         }
         else if (i == npnts) {
            TPW.p.z = z - endTol;
         }
         else {
            TPW.p.z = z;
         }
         cutPlane.setMeshToWorld (TPW);
         IntersectionContour contour =
            ComputeUtils.findPrimaryIsectContour (clippedMesh, cutPlane);
//         if (contour != null) {
//            count++;
//         } 
         if (contour != null) {
            Point3d cent = new Point3d();
            contour.computeCentroid (cent);
            r = ComputeUtils.computeContourRadius (contour, cent);
            if (r > maxr) {
               maxr = r;
            }
            cent.z = z; // reset z in case it was shrunk at the end points
            cpnts.add (cent);
         }
         else {
            System.out.println (
               "WARNING: findDonorCenterCurve: no centroid at z=" + z);
         }
      }
      clippedMesh.setMeshToWorld (TCW);  
      curve.setSingleSegment (cpnts, minz, maxz);
//      ArrayList<Vector3d> sampled_vals = curve.getSampledValues(30);
//      return TCW;
//      return maxr;
//      return sampled_vals;
      return curve;
   }      
   
   public ArrayList<FibulaDonorSegment> findDonorCutPlanes(float segSeparation, float minLength, int maxSegs, 
      ArrayList<Point3d> rdpLine, String fibulaPath, String mandiblePath, Plane planeL, Plane planeR,
      Point3d startPoint, RigidTransform3d TCW, Boolean leftToRight) throws IOException{
      
      if(!leftToRight) {
         Plane tmp = planeR; 
         planeR = planeL;
         planeL = tmp;
      }
   
      //Set input parameters
      double defaultSep = Double.valueOf (segSeparation);   
      double minSegLength = Double.valueOf (minLength);
      
      //Calculate RDP line
      //ArrayList<Point3d> rdpLine = computeRDPLine(contour, planeL, planeR, minSegLength, maxSegs);
         
      //Import mesh files
      PolygonalMesh mandible = new PolygonalMesh(mandiblePath);
      PolygonalMesh fibula = new PolygonalMesh(fibulaPath); //Need to set the TCW for it (setMeshToWorld(TCW))
      //fibula.inverseTransform (TCW);
      fibula.setMeshToWorld (TCW);   
//      PolygonalMesh fibula = new PolygonalMesh();
//      RigidTransform3d TCW = prepareFibula(fibula, fibulaPath, prox, dist);
      
      //Calculate segments in mandible space
      ArrayList<FibulaDonorSegment> segments = createSegmentSpecs(rdpLine, mandible, planeL, planeR, leftToRight);
         
      //Generate spline along the z-axis of the donor curve
      CubicHermiteSpline3d donorCurve = new CubicHermiteSpline3d();
      donorCurve = findDonorCenterCurve(donorCurve, fibula, 50);
      double ztop = donorCurve.getLastKnot().getS0();
           
      //Get the start point from fib fid
      Point3d p0 = new Point3d(startPoint);
            
      for (int i=0; i < segments.size(); i++) {
         FibulaDonorSegment seg = segments.get(i);
         double len = seg.myTPS0.p.distance (seg.myTPS1.p);
         //find segment end point along the fibula 
      
         Point3d p1 = findNextDonorPoint(p0, len, fibula, donorCurve);
         //use this to compute the segment transform 
         seg.myTSW_D.set(computeSegmentFrame(p0, p1, fibula));
         //compute any extra separation that we need to apply to p0
         RigidTransform3d TPW0_D = new RigidTransform3d();
         TPW0_D.mul (seg.myTSW_D, seg.myTPS0);
         double sep = computeExtraSegSeparation0(p0, TPW0_D, fibula, ztop);
         if (sep > 0) {
            p0 = findNextDonorPoint(p0, sep, fibula, donorCurve);
            p1 = findNextDonorPoint(p0, len, fibula, donorCurve);
            seg.myTSW_D.set (computeSegmentFrame(p0, p1, fibula));
         }
         RigidTransform3d TPW1_D = new RigidTransform3d();
         TPW1_D.mul (seg.myTSW_D, seg.myTPS1);
         sep = computeExtraSegSeparation1(p1, TPW1_D, fibula);
         sep += defaultSep;
         p0 = findNextDonorPoint(p1, sep, fibula, donorCurve);
         }
      return segments;
   }
   
   private double computeExtraSegSeparation0 (
      Point3d p0, RigidTransform3d TPW0_D, PolygonalMesh donorMesh, double ztop) {

      // find the intersection contour between the cut plane nad the donor, and
      // check (in donor coordinates) if the z coordinate of any of its points
      // extends above the z coordinate of p0.

      PolygonalMesh cutPlane = MeshFactory.createPlane (90, 90, 30, 30);
      cutPlane.setMeshToWorld (TPW0_D);
      IntersectionContour contour = 
         ComputeUtils.findPrimaryIsectContour (donorMesh, cutPlane);
      if (contour == null) {
         throw new NumericalException (
            "No intersection contour between donor and cut plane 0");
      }
      RigidTransform3d TDW = donorMesh.getMeshToWorld();
      // find max z value in donor coordinates
      double maxz = -INF;
      Point3d p_d = new Point3d(); // point in donor space
      for (Point3d p : contour) {
         p_d.inverseTransform (TDW, p);
         if (p_d.z > maxz) {
            maxz = p_d.z;
         }
      }
      // if maxz > p0.z in donor space, need to add more separation
      p_d.inverseTransform (TDW, p0);
      if (maxz > p_d.z) {
         if (Math.abs(ztop-maxz) < 1e-8) {
            // contour might have cut off at the top; need to compute
            // separation differently

            // intersect with a plane whose z axis is aligned with TDW
            RigidTransform3d TPW = new RigidTransform3d (TPW0_D);
            TPW.R.set (TDW.R); // align cut plane with donor
            cutPlane.setMeshToWorld (TPW);
            contour = ComputeUtils.findPrimaryIsectContour (donorMesh, cutPlane);
            if (contour == null) {
               throw new NumericalException (
                  "No intersection contour between donor and cut plane 0");
            }            
            // find contour radius
            Point3d cent = new Point3d();
            contour.computeCentroid (cent);
            double r = ComputeUtils.computeContourRadius (contour, cent);
            // set sep to 2*r*sin(theta), where theta is the angle between the
            // z axes of TPW0_D and TDW
            Vector3d zdirD = new Vector3d();
            Vector3d zdirP = new Vector3d();
            TDW.R.getColumn (2, zdirD);
            TPW0_D.R.getColumn (2, zdirP);
            Vector3d xprod = new Vector3d();
            xprod.cross (zdirD, zdirP);
            return 2*r*xprod.norm(); // sin(theta) = length of xprod            
         }
         else {
            return maxz - p_d.z;
         }
      }
      else {
         return 0;
      }
   }

   /**
    * Determines any extra separation needed before that start of another donor
    * segment to ensure that the last cut plane of the current segment will not
    * intersect it.
    */
   private double computeExtraSegSeparation1 (
      Point3d p1, RigidTransform3d TPW1_D, PolygonalMesh donorMesh) {
      // find the intersection contour between the cut plane nad the donor, and
      // check (in donor coordinates) if the z coordinate of any of its points
      // extends below the z coordinate of p1.

      PolygonalMesh cutPlane = MeshFactory.createPlane (90, 90, 30, 30);
      cutPlane.setMeshToWorld (TPW1_D);
      IntersectionContour contour =
         ComputeUtils.findPrimaryIsectContour (donorMesh, cutPlane);
      if (contour == null) {
         throw new NumericalException (
            "No intersection contour between donor and cut plane 1");
      }
      RigidTransform3d TDW = donorMesh.getMeshToWorld();
      // find min z value in donor coordinates
      double minz = INF;
      Point3d p_d = new Point3d(); // point in donor space
      for (Point3d p : contour) {
         p_d.inverseTransform (TDW, p);
         if (p_d.z < minz) {
            minz = p_d.z;
         }
      }
      // if minz < p1.z in donor space, add the diff to the separation
      p_d.inverseTransform (TDW, p1);
      if (minz < p_d.z) {
         return p_d.z - minz;
         //return p_d.z + minz;
      }
      else {
         return 0;
      }
   }
   
   /**
    * Compute a local transform for a plane that given a plane point and normal
    * in world coordinates.
    *
    * @param TLW transform from local to world coordinates
    * @param nrm plane normal in world coordinates
    * @param pnt plane point in world coordinates
    * @return transform from plane to world coordinates
    */
   private RigidTransform3d getPlaneTrans (
      RigidTransform3d TLW, Vector3d nrm, Point3d pos) {

      RigidTransform3d TPW = new RigidTransform3d();
      TPW.R.set (TLW.R);
      TPW.R.setZDirection (nrm);
      TPW.p.set (pos);
      RigidTransform3d TPL = new RigidTransform3d();
      TPL.mulInverseLeft (TLW, TPW); 
      return TPL;
   }

   /**
    * Compute the coordinate frame of a donor segment, wrt some mesh, using its
    * corresponding end points on the RDP line. The origin is given by the
    * midpoint the points, the z direction is parallel to pos0 - pos1, and the
    * y direction is set to be as close as possible to the average of the
    * estimated surface normals at pos0 and pos1.
    */
   public static RigidTransform3d computeSegmentFrame (
      Point3d pos0, Point3d pos1, PolygonalMesh mesh) {

      Point3d segCenter = new Point3d();
      segCenter.add (pos0, pos1);
      segCenter.scale (0.5);
      Vector3d zvec = new Vector3d();
      zvec.sub (pos0, pos1);
      zvec.normalize();     
      // compute average of the estimate surface normals at pos0 and pos1
      Vector3d yvec = new Vector3d();      
      yvec.set (ComputeUtils.estimateSurfaceNormal (pos0, mesh));
      yvec.add (ComputeUtils.estimateSurfaceNormal (pos1, mesh));
      // remove y component parallel to z
      yvec.scaledAdd (-yvec.dot(zvec), zvec);
      yvec.normalize();
      // Compute new segment coordinate frame TSW
      RigidTransform3d TSW = new RigidTransform3d();
      TSW.R.setYZDirections (yvec, zvec);
      TSW.p.set (segCenter);
      return TSW;
   }
   
   /**
    * Modify the orientation of transform {@code T1} so that the y axes of both
    * {@code T0} and {@code T1} are both aligned with respect to the average z
    * direction of both transforms; i.e., each transform's y axis has the same
    * rotation about about the average z direction.
    */
   public static void alignYZ (RigidTransform3d T1, RigidTransform3d T0) {
      Vector3d y0 = new Vector3d();
      Vector3d x1 = new Vector3d();
      Vector3d y1 = new Vector3d();

      T0.R.getColumn (1, y0);
      T1.R.getColumn (0, x1);
      T1.R.getColumn (1, y1);

      Vector3d zavg = averageZDir (T1, T0);
      Vector3d u = new Vector3d();
      u.cross (y0, zavg);

      // rotate y1 about z1 such that y1 . u = 0. If the rotation is performed
      // by y1' = -s x1 + c y1, where s and c are the sine and cosine of the
      // rotation, we want -s (x1 . u) + c (y1 . u) = 0, or s a = c b, where a
      // = x1 . u and b = y1 . u
      double a = x1.dot (u);
      double b = y1.dot (u);
      // solve for s and c
      double mag = Math.sqrt (a*a + b*b);
      if (mag != 0) {
         double s = b/mag;
         double c = a/mag;
         RotationMatrix3d RZ =
            new RotationMatrix3d (c, -s, 0,  s, c, 0,  0, 0,1);
         T1.R.mul (RZ);
      }
   }
   
   /**
    * Find a point {@code p1} along the (fibula) donor segment that is {@code
    * len} distance away from a previous point {@code p0}. We start by moving
    * in a direction parallel to the donor centerline. We then project {@code
    * p1} to the donor surface and move it so that is still {@code len} away
    * from {@code p1}, and iterate this until {@code p1} is sufficiently close
    * to the donor surface.
    */
   public Point3d findNextDonorPoint (
      Point3d p0, double len, PolygonalMesh donorMesh,
      CubicHermiteSpline3d donorCurve) {

      Point3d p1 = new Point3d();

      // "_d" denotes quantities in donor space
      RigidTransform3d TDW = donorMesh.getMeshToWorld(); //This is actually TCW. Need to send this in from the donor mesh. 
      Point3d p0_d = new Point3d(p0);
      p0_d.inverseTransform (TDW);

      //start point and end point on the donor curve
      Point3d cp0_d = new Point3d(donorCurve.eval (p0_d.z)); 
      Point3d cp1_d = new Point3d(donorCurve.eval (p0_d.z-len)); 

      Vector3d u = new Vector3d();
      u.sub (cp1_d, cp0_d);
      u.transform (TDW);
      p1.scaledAdd (len/u.norm(), u, p0);
      //return p1;
      double tol = len*1e-8;
      int maxIters = 100;
      //return p1;
      for (int iter=1; iter<=maxIters; iter++) {
         double dist = projectToDonor (p1, donorMesh, donorCurve, TDW);
         if (dist == -1) {
            throw new NumericalException ("project to donor failed");
         }
         // make sure || p1-p0 || = len
         u.sub (p1, p0);
         p1.scaledAdd (len/u.norm(), u, p0);
         if (dist <= tol) {
            return p1;
         }
      }
      throw new NumericalException (
         "findNextDonorPoint: iteration count exceeded");
   }
   
   private double projectToDonor (
      Point3d p1, PolygonalMesh donorMesh,
      CubicHermiteSpline3d donorCurve, RigidTransform3d TDW) {

      Point3d p1_d = new Point3d(p1);
      p1_d.inverseTransform (TDW);
      
      Point3d cp1_d = new Point3d(donorCurve.eval (p1_d.z));
      Vector3d ray = new Vector3d();
      ray.sub (p1_d, cp1_d);
      ray.transform (TDW);
      BVFeatureQuery query = new BVFeatureQuery();
      Point3d pp = query.nearestPointAlongRay (donorMesh, p1, ray);
      if (pp != null) {
         double d = p1.distance(pp);
         p1.set (pp);
         return d;
      }
      ray.negate();
      pp = query.nearestPointAlongRay (donorMesh, p1, ray);
      if (pp != null) {
         double d = p1.distance(pp);
         p1.set (pp);
         return d;
      }
      double d = query.distanceToMesh (p1, donorMesh, p1);
      if (d >= 0) {
         System.out.println ("WARNING: projectToDonor failed along ray");
         return d;
      }
      else {
         System.out.println (
            "WARNING: projectToDonor failed for point "+p1);
         return -1;
      }
   }
   
   /**
    * Compute the average z direction of two transforms.
    */
   private static Vector3d averageZDir (
      RigidTransform3d T0, RigidTransform3d T1) {
      Vector3d z0 = new Vector3d();
      Vector3d z1 = new Vector3d();
      T0.R.getColumn (2, z0);
      T1.R.getColumn (2, z1);
      z0.add (z1);
      z0.normalize();
      return z0;      
   }
   
   //GET fibula donor segment transforms
   public RigidTransform3d getTPS0(FibulaDonorSegment segment){
      return segment.myTPS0;
   }
   
   public RigidTransform3d getTPS1(FibulaDonorSegment segment) {
      return segment.myTPS1;
   }
   
   public RigidTransform3d getTSWM(FibulaDonorSegment segment) {
      return segment.myTSW_M;
   }
   
   public RigidTransform3d getTSWD(FibulaDonorSegment segment) {
      return segment.myTSW_D;
   } 
   
   public ArrayList<Double> getTPS0_Array(FibulaDonorSegment segment){
      ArrayList<Double> TPS0 = changeTransformToArray(segment.myTPS0);
      return TPS0;
   }
   
   public ArrayList<Double> getTPS1_Array(FibulaDonorSegment segment){
      ArrayList<Double> TPS1 = changeTransformToArray(segment.myTPS1);
      return TPS1;
   }
   
   public ArrayList<Double> getTSWM_Array(FibulaDonorSegment segment){
      ArrayList<Double> TSW_M = changeTransformToArray(segment.myTSW_M);
      return TSW_M;
   }
   
   public ArrayList<Double> getTSWD_Array(FibulaDonorSegment segment){
      ArrayList<Double> TSW_D = changeTransformToArray(segment.myTSW_D);
      return TSW_D;
   }
   
   /**
    * Create the clipped donor by removing the top and bottom parts of the
    * donor. This is done by intersecting the donor (in donor coordinates) with
    * cut planes perpendicular to the z axis.
    * @throws IOException 
    */
   public RigidTransform3d prepareFibula (String inputPath, String outputPath, float proximal, float distal) 
   throws IOException {
      double proxDist = Double.valueOf (proximal);
      double distalDist = Double.valueOf (distal);
      
      PolygonalMesh donorMesh = new PolygonalMesh(inputPath);

      RigidTransform3d TCW = new RigidTransform3d();
      
      PolygonalMesh clippedMesh;
      RigidTransform3d TDW = donorMesh.getMeshToWorld(); // donor pose wrt world
      OBB boundingBox = donorMesh.computeOBB();
      Vector3d halfWidths = boundingBox.getHalfWidths();
      double halfLen = halfWidths.maxElement();
      boundingBox.getTransform (TCW); 
      TCW.mul (TDW, TCW); // set TCW to pose of clipped donor wrt world
      // if necessary, adjust TCW so that z points along the longest box axis
      if (halfWidths.maxAbsIndex() == 0) {
         TCW.R.mulRotY (Math.PI/2); // longest axis is x; rotate about y
      }
      else if (halfWidths.maxAbsIndex() == 1) {
         TCW.R.mulRotX (-Math.PI/2); // longest axis is y; rotate about x
      }
      PolygonalMesh cutPlane = MeshFactory.createPlane (100, 100, 30, 30);
      RigidTransform3d TPW = new RigidTransform3d(); // cut plane pose wrt world
      SurfaceMeshIntersector intersector = new SurfaceMeshIntersector();
      double clippedLen = 2*halfLen-proxDist-distalDist; // clipped donor length

      TPW.set (TCW);
      TPW.mulXyz (0, 0, halfLen-proxDist);
      cutPlane.setMeshToWorld (TPW);
      clippedMesh = intersector.findIntersection (donorMesh, cutPlane);
      TPW.mulXyz (0, 0, -clippedLen);
      cutPlane.setMeshToWorld (TPW);
      clippedMesh = intersector.findDifference01 (clippedMesh, cutPlane);
      clippedMesh.inverseTransform (TCW); //inverse of C to world so we put it into C-coordinates
//      GenericMeshWriter.writeMesh (outputPath, clippedMesh);
      File output = new File(outputPath);
      writeMesh(output, clippedMesh);
      return TCW;
   }
   
   private void writeMesh (File file, MeshBase mesh) throws IOException {
      if (!mesh.getMeshToWorld().isIdentity()) {
         mesh = mesh.clone();
         mesh.transform (mesh.getMeshToWorld());
      }
      GenericMeshWriter.writeMesh (file, mesh);      
   }
   
   public CubicHermiteSpline3d findDonorCurve(String fibulaPath, RigidTransform3d TCW,
      float proximal, float distal) throws IOException {
      CubicHermiteSpline3d donorCurve = new CubicHermiteSpline3d();
      PolygonalMesh fibula = new PolygonalMesh(fibulaPath);
      fibula.setMeshToWorld (TCW);   
      CubicHermiteSpline3d curve = findDonorCenterCurve(donorCurve, fibula, 50);
//      ArrayList<Vector3d> curve = findDonorCenterCurve(donorCurve, fibula, 50);
//      double ztop = curve.getLastKnot().getS0();
      return curve;
   }
   
//   public Point3d findNextDonorPointTest (
//      Point3d p0, double len, String donorMeshPath,
//      CubicHermiteSpline3d donorCurve, RigidTransform3d TCW) throws IOException {
//      PolygonalMesh donorMesh = new PolygonalMesh(donorMeshPath);
//      donorMesh.setMeshToWorld (TCW);   
//      
//      Point3d p1 = new Point3d();
//   
//      // "_d" denotes quantities in donor space
//      RigidTransform3d TDW = donorMesh.getMeshToWorld(); //This is actually TCW. Need to send this in from the donor mesh. 
//      Point3d p0_d = new Point3d(p0);
//      p0_d.inverseTransform (TDW);
////      return TDW;
//      //start point and end point on the donor curve
//      Point3d cp0_d = new Point3d(donorCurve.eval (p0_d.z)); 
//      Point3d cp1_d = new Point3d(donorCurve.eval (p0_d.z-len)); 
//   
//      Vector3d u = new Vector3d();
//      u.sub (cp1_d, cp0_d);
//      u.transform (TDW);
//      p1.scaledAdd (len/u.norm(), u, p0);
//      //return p1;
//      double tol = len*1e-8;
//      int maxIters = 100;
//      //return p1;
//      for (int iter=1; iter<=maxIters; iter++) {
//         double dist = projectToDonor (p1, donorMesh, donorCurve, TDW);
//         if (dist == -1) {
//            throw new NumericalException ("project to donor failed");
//         }
//         // make sure || p1-p0 || = len
//         u.sub (p1, p0);
//         p1.scaledAdd (len/u.norm(), u, p0);
//         if (dist <= tol) {
//            return p1;
//         }
//      }
//      throw new NumericalException (
//         "findNextDonorPoint: iteration count exceeded");
//   }
   
   public Vector3d getCentroid(String meshpath) throws IOException {
      PolygonalMesh mesh = new PolygonalMesh(meshpath);
      Vector3d centroid = new Vector3d();
      mesh.computeCentroid (centroid);
      return centroid;
   }
}
