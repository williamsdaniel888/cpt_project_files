#!/usr/bin/env python

# ROS python API
import rospy
# Joy message structure
from sensor_msgs.msg import Joy
# 3D point & Stamped Pose msgs
from geometry_msgs.msg import Point, PoseStamped
# import all mavros messages and services
from mavros_msgs.msg import *
from mavros_msgs.srv import *

# Flight modes class
# Flight modes are activated using ROS services
class fcuModes:
    def __init__(self,name):
        self.name = name
        pass

    def setArm(self):
        rospy.wait_for_service(self.name+'/mavros/cmd/arming')
        try:
            armService = rospy.ServiceProxy(self.name+'/mavros/cmd/arming', mavros_msgs.srv.CommandBool)
            armService(True)
        except rospy.ServiceException, e:
            print "Service arming call failed: %s"%e

    def setDisarm(self):
        rospy.wait_for_service(self.name+'/mavros/cmd/arming')
        try:
            armService = rospy.ServiceProxy(self.name+'/mavros/cmd/arming', mavros_msgs.srv.CommandBool)
            armService(False)
        except rospy.ServiceException, e:
            print "Service disarming call failed: %s"%e

    def setStabilizedMode(self):
        rospy.wait_for_service(self.name+'/mavros/set_mode')
        try:
            flightModeService = rospy.ServiceProxy(self.name+'/mavros/set_mode', mavros_msgs.srv.SetMode)
            flightModeService(custom_mode='STABILIZED')
        except rospy.ServiceException, e:
            print "service set_mode call failed: %s. Stabilized Mode could not be set."%e

    def setOffboardMode(self):
        rospy.wait_for_service(self.name+'/mavros/set_mode')
        try:
            flightModeService = rospy.ServiceProxy(self.name+'/mavros/set_mode', mavros_msgs.srv.SetMode)
            flightModeService(custom_mode='OFFBOARD')
        except rospy.ServiceException, e:
            print "service set_mode call failed: %s. Offboard Mode could not be set."%e

    def setAltitudeMode(self):
        rospy.wait_for_service(self.name+'/mavros/set_mode')
        try:
            flightModeService = rospy.ServiceProxy(self.name+'/mavros/set_mode', mavros_msgs.srv.SetMode)
            flightModeService(custom_mode='ALTCTL')
        except rospy.ServiceException, e:
            print "service set_mode call failed: %s. Altitude Mode could not be set."%e

    def setPositionMode(self):
        rospy.wait_for_service(self.name+'/mavros/set_mode')
        try:
            flightModeService = rospy.ServiceProxy(self.name+'/mavros/set_mode', mavros_msgs.srv.SetMode)
            flightModeService(custom_mode='POSCTL')
        except rospy.ServiceException, e:
            print "service set_mode call failed: %s. Position Mode could not be set."%e

    def setAutoLandMode(self):
        rospy.wait_for_service(self.name+'/mavros/set_mode')
        try:
            flightModeService = rospy.ServiceProxy(self.name+'/mavros/set_mode', mavros_msgs.srv.SetMode)
            flightModeService(custom_mode='AUTO.LAND')
        except rospy.ServiceException, e:
              print "service set_mode call failed: %s. Autoland Mode could not be set."%e

# Main class: Converts joystick commands to position setpoints
class Controller:
    # initialization method
    def __init__(self):
        # Drone state
        self.state = State()
        # Instantiate a setpoints message
        self.sp         = PositionTarget()
        # set the flag to use position setpoints and yaw angle
        self.sp.type_mask    = int('010111111000', 2)
        # LOCAL_NED
        self.sp.coordinate_frame= 1

        # We will fly at a fixed altitude for now
        # Altitude setpoint, [meters]
        self.ALT_SP        = 1
        # update the setpoint message with the required altitude
        self.sp.position.z    = self.ALT_SP

        # Instantiate a joystick message
        self.joy_msg        = Joy()
        # initialize
        self.joy_msg.axes=[0.0, 0.0, 0.0]

        # Step size for position update
        self.STEP_SIZE = 1.0
        
        # Fence. We will assume a square fence for now
        self.FENCE_LIMIT = 3.0

        # A Message for the current local position of the drone
        self.local_pos = Point(0.0, 0.0, 0.0)

    # Callbacks

    ## local position callback
    def posCb(self, msg):
        self.local_pos.x = msg.pose.position.x
        self.local_pos.y = msg.pose.position.y
        self.local_pos.z = msg.pose.position.z

    ## joystick callback
    def joyCb(self, msg):
        self.joy_msg = msg

    ## Drone State callback
    def stateCb(self, msg):
        self.state = msg

    ## Update setpoint message
    def updateSp(self,x,y):
        #x = -1.0*self.joy_msg.axes[1]
        #y = -1.0*self.joy_msg.axes[0]
        self.sp.position.x = x #self.local_pos.x + self.STEP_SIZE*x
        self.sp.position.y = y #self.local_pos.y + self.STEP_SIZE*y

# Main function
def main():

    # initiate node
    rospy.init_node('setpoint_node', anonymous=True)

    # flight mode object
    modes_0 = fcuModes('uav0')
    modes_1 = fcuModes('uav1')
    # controller object
    cnt_0 = Controller()
    cnt_1 = Controller()


    # ROS loop rate, [Hz]
    rate = rospy.Rate(20.0)

    # Subscribe to drone state
    rospy.Subscriber('uav0/mavros/state', State, cnt_0.stateCb)
    rospy.Subscriber('uav1/mavros/state', State, cnt_1.stateCb)

    # Subscribe to drone's local position
    rospy.Subscriber('uav0/mavros/local_position/pose', PoseStamped, cnt_0.posCb)
    rospy.Subscriber('uav1/mavros/local_position/pose', PoseStamped, cnt_1.posCb)
    # subscribe to joystick topic
    #rospy.Subscriber('joy', Joy, cnt_0.joyCb)
    #rospy.Subscriber('joy', Joy, cnt_1.joyCb)

    # Setpoint publisher
    sp_pub_0 = rospy.Publisher('uav0/mavros/setpoint_raw/local', PositionTarget, queue_size=1)
    sp_pub_1 = rospy.Publisher('uav1/mavros/setpoint_raw/local', PositionTarget, queue_size=1)


    # Make sure the drone is armed
    while not cnt_0.state.armed:
        modes_0.setArm()
        rate.sleep()
    #while not cnt_1.state.armed:
        modes_1.setArm()
        rate.sleep()

    # We need to send few setpoint messages, then activate OFFBOARD mode, to take effect
    k=0
    while k<10:
        sp_pub_0.publish(cnt_0.sp)
        sp_pub_1.publish(cnt_1.sp)
        rate.sleep()
        k = k+1

    # activate OFFBOARD mode
    modes_0.setOffboardMode()
    modes_1.setOffboardMode()

    # ROS main loop
    while not rospy.is_shutdown():
        cnt_0.updateSp(0,0)
        cnt_1.updateSp(0,0)
        sp_pub_0.publish(cnt_0.sp)
        sp_pub_1.publish(cnt_1.sp)
        rate.sleep()


if __name__ == '__main__':
    try:
        main()
    except rospy.ROSInterruptException:
        pass