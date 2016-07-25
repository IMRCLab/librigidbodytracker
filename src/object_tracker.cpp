#include "libobjecttracker/object_tracker.h"

// PCL
#include <pcl/point_cloud.h>
#include <pcl/point_types.h>
#include <pcl/common/transforms.h>
#include <pcl/registration/icp.h>
#include <pcl/registration/transformation_estimation_2D.h>
// #include <pcl/registration/transformation_estimation_lm.h>

// TEMP for debug
#include <cstdio>

using Point = pcl::PointXYZ;
using Cloud = pcl::PointCloud<Point>;
using ICP = pcl::IterativeClosestPoint<Point, Point>;

static Eigen::Vector3f pcl2eig(Point p)
{
  return Eigen::Vector3f(p.x, p.y, p.z);
}

static Point eig2pcl(Eigen::Vector3f v)
{
  return Point(v.x(), v.y(), v.z());
}

namespace libobjecttracker {

/////////////////////////////////////////////////////////////

Object::Object(
  size_t markerConfigurationIdx,
  size_t dynamicsConfigurationIdx,
  const Eigen::Affine3f& initialTransformation)
  : m_markerConfigurationIdx(markerConfigurationIdx)
  , m_dynamicsConfigurationIdx(dynamicsConfigurationIdx)
  , m_lastTransformation(initialTransformation)
  , m_lastValidTransform()
  , m_lastTransformationValid(false)
{
}

const Eigen::Affine3f& Object::transformation() const
{
  return m_lastTransformation;
}

bool Object::lastTransformationValid() const
{
  return m_lastTransformationValid;
}

/////////////////////////////////////////////////////////////

ObjectTracker::ObjectTracker(
  const std::vector<DynamicsConfiguration>& dynamicsConfigurations,
  const std::vector<MarkerConfiguration>& markerConfigurations,
  const std::vector<Object>& objects)
  : m_markerConfigurations(markerConfigurations)
  , m_dynamicsConfigurations(dynamicsConfigurations)
  , m_objects(objects)
  , m_initialized(false)
  , m_init_attempts(0)
  , m_logWarn()
{

}

void ObjectTracker::update(Cloud::Ptr pointCloud)
{
  update(std::chrono::high_resolution_clock::now(), pointCloud);
}

void ObjectTracker::update(std::chrono::high_resolution_clock::time_point time,
  Cloud::Ptr pointCloud)
{
  runICP(time, pointCloud);
}

const std::vector<Object>& ObjectTracker::objects() const
{
  return m_objects;
}

void ObjectTracker::setLogWarningCallback(
  std::function<void(const std::string&)> logWarn)
{
  m_logWarn = logWarn;
}

bool ObjectTracker::initialize(Cloud::ConstPtr markersConst)
{
  // we need to mutate the cloud by deleting points
  // once they are assigned to an object
  Cloud::Ptr markers(new Cloud(*markersConst));

  size_t const nObjs = m_objects.size();

  ICP icp;
  icp.setMaximumIterations(5);
  icp.setInputTarget(markers);

  // prepare for knn query
  std::vector<int> nearestIdx;
  std::vector<float> nearestSqrDist;
  std::vector<int> objTakePts;
  pcl::KdTreeFLANN<Point> kdtree;
  kdtree.setInputCloud(markers);

  // compute the distance between the closest 2 objects in the nominal configuration
  // we will use this value to limit allowed deviation from nominal positions
  float closest = FLT_MAX;
  for (int i = 0; i < nObjs; ++i) {
    auto pi = m_objects[i].center();
    for (int j = i + 1; j < nObjs; ++j) {
      float dist = (pi - m_objects[j].center()).norm();
      closest = std::min(closest, dist);
    }
  }
  float const max_deviation = closest / 3;

  printf("Object tracker: limiting distance from nominal position "
    "to %f meters\n", max_deviation);

  bool allFitsGood = true;
  for (int iObj = 0; iObj < nObjs; ++iObj) {
    Object& object = m_objects[iObj];
    Cloud::Ptr &objMarkers =
      m_markerConfigurations[object.m_markerConfigurationIdx];
    icp.setInputSource(objMarkers);

    // find the points nearest to the object's nominal position
    // (initial pos was loaded into lastTransformation from config file)
    size_t const objNpts = objMarkers->size();
    nearestIdx.resize(objNpts);
    nearestSqrDist.resize(objNpts);
    auto nominalCenter = eig2pcl(object.center());
    kdtree.nearestKSearch(nominalCenter, objNpts, nearestIdx, nearestSqrDist);

    // only try to fit the object if the k nearest neighbors
    // are reasonably close to the nominal object position
    Eigen::Vector3f actualCenter(0, 0, 0);
    for (int i = 0; i < objNpts; ++i) {
      actualCenter += pcl2eig((*markers)[nearestIdx[i]]);
    }
    actualCenter /= objNpts;
    if ((actualCenter - pcl2eig(nominalCenter)).norm() > max_deviation) {
      std::cout << "error: nearest neighbors of object " << iObj
                << " are centered at " << actualCenter
                << " instead of " << nominalCenter << "\n";
      allFitsGood = false;
      continue;
    }

    // try ICP with guesses of many different yaws about knn centroid
    Cloud result;
    static int const N_YAW = 20;
    double bestErr = DBL_MAX;
    Eigen::Affine3f bestTransformation;
    for (int i = 0; i < N_YAW; ++i) {
      float yaw = i * (2 * M_PI / N_YAW);
      Eigen::Matrix4f tryMatrix = pcl::getTransformation(
        actualCenter.x(), actualCenter.y(), actualCenter.z(),
        0, 0, yaw).matrix();
      icp.align(result, tryMatrix);
      double err = icp.getFitnessScore();
      if (err < bestErr) {
        bestErr = err;
        bestTransformation = icp.getFinalTransformation();
      }
    }

    // check that the best fit was actually good
    static double const INIT_MAX_HAUSDORFF_DIST2 = 0.005 * 0.005; // 5mm
    nearestIdx.resize(1);
    nearestSqrDist.resize(1);
    objTakePts.resize(objNpts);
    bool fitGood = true;
    for (size_t i = 0; i < objNpts; ++i) {
      auto p = bestTransformation * pcl2eig((*objMarkers)[i]);
      kdtree.nearestKSearch(eig2pcl(p), 1, nearestIdx, nearestSqrDist);
      objTakePts[i] = nearestIdx[0];
      if (nearestSqrDist[0] > INIT_MAX_HAUSDORFF_DIST2) {
        fitGood = false;
        std::cout << "error: nearest neighbor of marker " << i
                  << " in object " << iObj << " is "
                  << 1000 * sqrt(nearestSqrDist[0]) << "mm from nominal\n";
      }
    }

    // if the fit was good, this object "takes" the markers, and they become
    // unavailable to all other objects so we don't double-assign markers
    // (TODO: this is so greedy... do we need a more global approach?)
    if (fitGood) {
      object.m_lastTransformation = bestTransformation;
      // remove highest indices first
      std::sort(objTakePts.rbegin(), objTakePts.rend());
      for (int idx : objTakePts) {
        markers->erase(markers->begin() + idx);
      }
      // update search structures after deleting markers
      icp.setInputTarget(markers);
      kdtree.setInputCloud(markers);
    }
    allFitsGood = allFitsGood && fitGood;
  }

  ++m_init_attempts;
  return allFitsGood;
}

void ObjectTracker::runICP(std::chrono::high_resolution_clock::time_point stamp,
  Cloud::ConstPtr markers)
{
  m_initialized = m_initialized || initialize(markers);
  if (!m_initialized) {
    logWarn(
      "Object tracker initialization failed - "
      "check that position is correct, all markers are visible, "
      "and marker configuration matches config file");
  }

  ICP icp;
  // pcl::registration::TransformationEstimationLM<Point, Point>::Ptr trans(new pcl::registration::TransformationEstimationLM<Point, Point>);
  // pcl::registration::TransformationEstimation2D<Point, Point>::Ptr trans(new pcl::registration::TransformationEstimation2D<Point, Point>);
  // pcl::registration::TransformationEstimation3DYaw<Point, Point>::Ptr trans(new pcl::registration::TransformationEstimation3DYaw<Point, Point>);
  // icp.setTransformationEstimation(trans);


  // // Set the maximum number of iterations (criterion 1)
  icp.setMaximumIterations(5);
  // // Set the transformation epsilon (criterion 2)
  // icp.setTransformationEpsilon(1e-8);
  // // Set the euclidean distance difference epsilon (criterion 3)
  // icp.setEuclideanFitnessEpsilon(1);

  icp.setInputTarget(markers);

  for (auto& object : m_objects) {
    object.m_lastTransformationValid = false;

    std::chrono::duration<double> elapsedSeconds = stamp-object.m_lastValidTransform;
    double dt = elapsedSeconds.count();

    // Set the max correspondence distance
    // TODO: take max here?
    const DynamicsConfiguration& dynConf = m_dynamicsConfigurations[object.m_dynamicsConfigurationIdx];
    float maxV = dynConf.maxXVelocity;
    icp.setMaxCorrespondenceDistance(maxV * dt);
    // ROS_INFO("max: %f", maxV * dt);

    // Update input source
    icp.setInputSource(m_markerConfigurations[object.m_markerConfigurationIdx]);

    // Perform the alignment
    Cloud result;
    auto deltaPos = Eigen::Translation3f(dt * object.m_velocity);
    auto predictTransform = deltaPos * object.m_lastTransformation;
    icp.align(result, predictTransform.matrix());
    if (!icp.hasConverged()) {
      // ros::Time t = ros::Time::now();
      // ROS_INFO("ICP did not converge %d.%d", t.sec, t.nsec);
      logWarn("ICP did not converge!");
      continue;
    }

    // Obtain the transformation that aligned cloud_source to cloud_source_registered
    Eigen::Matrix4f transformation = icp.getFinalTransformation();

    Eigen::Affine3f tROTA(transformation);
    float x, y, z, roll, pitch, yaw;
    pcl::getTranslationAndEulerAngles(tROTA, x, y, z, roll, pitch, yaw);

    // Compute changes:
    float last_x, last_y, last_z, last_roll, last_pitch, last_yaw;
    pcl::getTranslationAndEulerAngles(object.m_lastTransformation, last_x, last_y, last_z, last_roll, last_pitch, last_yaw);

    float vx = (x - last_x) / dt;
    float vy = (y - last_y) / dt;
    float vz = (z - last_z) / dt;
    float wroll = (roll - last_roll) / dt;
    float wpitch = (pitch - last_pitch) / dt;
    float wyaw = (yaw - last_yaw) / dt;

    // ROS_INFO("v: %f,%f,%f, w: %f,%f,%f, dt: %f", vx, vy, vz, wroll, wpitch, wyaw, dt);

    if (   fabs(vx) < dynConf.maxXVelocity
        && fabs(vy) < dynConf.maxYVelocity
        && fabs(vz) < dynConf.maxZVelocity
        && fabs(wroll) < dynConf.maxRollRate
        && fabs(wpitch) < dynConf.maxPitchRate
        && fabs(wyaw) < dynConf.maxYawRate
        && fabs(roll) < dynConf.maxRoll
        && fabs(pitch) < dynConf.maxPitch
        && icp.getFitnessScore() < dynConf.maxFitnessScore)
    {
      object.m_velocity = (tROTA.translation() - object.center()) / dt;
      object.m_lastTransformation = tROTA;
      object.m_lastValidTransform = stamp;
      object.m_lastTransformationValid = true;
    } else {
      std::stringstream sstr;
      sstr << "Dynamic check failed" << std::endl;
      if (fabs(vx) >= dynConf.maxXVelocity) {
        sstr << "vx: " << vx << " >= " << dynConf.maxXVelocity << std::endl;
      }
      if (fabs(vy) >= dynConf.maxYVelocity) {
        sstr << "vy: " << vy << " >= " << dynConf.maxYVelocity << std::endl;
      }
      if (fabs(vz) >= dynConf.maxZVelocity) {
        sstr << "vz: " << vz << " >= " << dynConf.maxZVelocity << std::endl;
      }
      if (fabs(wroll) >= dynConf.maxRollRate) {
        sstr << "wroll: " << wroll << " >= " << dynConf.maxRollRate << std::endl;
      }
      if (fabs(wpitch) >= dynConf.maxPitchRate) {
        sstr << "wpitch: " << wpitch << " >= " << dynConf.maxPitchRate << std::endl;
      }
      if (fabs(wyaw) >= dynConf.maxYawRate) {
        sstr << "wyaw: " << wyaw << " >= " << dynConf.maxYawRate << std::endl;
      }
      if (fabs(roll) >= dynConf.maxRoll) {
        sstr << "roll: " << roll << " >= " << dynConf.maxRoll << std::endl;
      }
      if (fabs(pitch) >= dynConf.maxPitch) {
        sstr << "pitch: " << pitch << " >= " << dynConf.maxPitch << std::endl;
      }
      if (icp.getFitnessScore() >= dynConf.maxFitnessScore) {
        sstr << "fitness: " << icp.getFitnessScore() << " >= " << dynConf.maxFitnessScore << std::endl;
      }
      logWarn(sstr.str());
    }
  }

}

void ObjectTracker::logWarn(const std::string& msg)
{
  if (m_logWarn) {
    m_logWarn(msg);
  }
}

} // namespace libobjecttracker

#ifdef STANDALONE
#include "stdio.h"
#include "cloudlog.hpp"
int main()
{
  libobjecttracker::ObjectTracker ot({}, {}, {});
  PointCloudLogger logger;
  PointCloudPlayer player;
  player.play(ot);
  puts("test OK");
}
#endif // STANDALONE
