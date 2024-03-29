# surface_inspector
Python code for surface inspection is supposed to used especially for agricultural products, which requires Flir(previously PointGrey) USB3 camera with Spinnaker SDK, and PySpin, python module(1.26.0.31) with Opencv, PyQt5, PySerial, and etc.
It is capable of Color Correction, Binarization, Lens Distortion Correction, and multiple ROI processing.
The color Correction is implemented with OpenCV.mcc and OpenCV.ccm (i.e. Color Correction matrix) from MecBeth Color Chart.
As well as the Lens Distortion Correction provides generic model as options of fisheye, and omnidirectional model in the form of modified opencv ccalib package.
The Binarization is capable of look and feel control by RangeSlider with sliding both of lower, and higher values.

# Screenshot
## Calibration Panel
![alt ROI Setting + Calibration](Screenshot_2021-05-14_14-22-56.png)

## Binarization Penel
![alt ROI Setting + Binarization](Screenshot_2021-05-14_14-23-25.png)

## Setting Panel for tuning camera
![alt ROI Setting + Camera Setting](Screenshot_2021-05-14_14-23-41.png)

# Dependencies
## 1. Install Spinnaker SDK.
### 1.1. The dependencies.
<pre><code>$ apt install libavcodec-ffmpeg56 libavformat-ffmpeg56 libswscale-ffmpeg3 libswresample-ffmpeg1 libavutil-ffmpeg54 libusb-1.0-0 libgtkmm-2.4-dev</code></pre>
#### 1.1.1. Workaround
<pre><code>$ vi /etc/apt/source.list
	deb http://debian-archive.trafficmanager.net/debian/ stretch main
$ apt update
$ apt install libswscale4 libavcodec57 libavformat57</code></pre>
### 1.2. Spinnaker
<pre><code>$ sh install_spinnaker.sh
This is a script to assist with installation of the Spinnaker SDK.
Would you like to continue and install all the Spinnaker SDK packages?
[Y/n] $ 

Installing Spinnaker packages...
Selecting previously unselected package libspinnaker1-dev.
(Reading database ... 431320 files and directories currently installed.)
Preparing to unpack libspinnaker-1.26.0.31_amd64-dev.deb ...
Unpacking libspinnaker1-dev (1.26.0.31) ...
Selecting previously unselected package libspinnaker1.
Preparing to unpack libspinnaker-1.26.0.31_amd64.deb ...
Unpacking libspinnaker1 (1.26.0.31) ...
Selecting previously unselected package libspinnaker-c1-dev.
Preparing to unpack libspinnaker-c-1.26.0.31_amd64-dev.deb ...
Unpacking libspinnaker-c1-dev (1.26.0.31) ...
Selecting previously unselected package libspinnaker-c1.
Preparing to unpack libspinnaker-c-1.26.0.31_amd64.deb ...
Unpacking libspinnaker-c1 (1.26.0.31) ...
Setting up libspinnaker1 (1.26.0.31) ...
Setting up libspinnaker-c1 (1.26.0.31) ...
Setting up libspinnaker1-dev (1.26.0.31) ...
Setting up libspinnaker-c1-dev (1.26.0.31) ...
Selecting previously unselected package libspinvideo1-dev.
(Reading database ... 431571 files and directories currently installed.)
Preparing to unpack libspinvideo-1.26.0.31_amd64-dev.deb ...
Unpacking libspinvideo1-dev (1.26.0.31) ...
Selecting previously unselected package libspinvideo1.
Preparing to unpack libspinvideo-1.26.0.31_amd64.deb ...
Unpacking libspinvideo1 (1.26.0.31) ...
Selecting previously unselected package libspinvideo-c1-dev.
Preparing to unpack libspinvideo-c-1.26.0.31_amd64-dev.deb ...
Unpacking libspinvideo-c1-dev (1.26.0.31) ...
Selecting previously unselected package libspinvideo-c1.
Preparing to unpack libspinvideo-c-1.26.0.31_amd64.deb ...
Unpacking libspinvideo-c1 (1.26.0.31) ...
Setting up libspinvideo1-dev (1.26.0.31) ...
Setting up libspinvideo1 (1.26.0.31) ...
Setting up libspinvideo-c1-dev (1.26.0.31) ...
Setting up libspinvideo-c1 (1.26.0.31) ...
Selecting previously unselected package spinview-qt1-dev.
(Reading database ... 431656 files and directories currently installed.)
Preparing to unpack spinview-qt-1.26.0.31_amd64-dev.deb ...
Unpacking spinview-qt1-dev (1.26.0.31) ...
Selecting previously unselected package spinview-qt1.
Preparing to unpack spinview-qt-1.26.0.31_amd64.deb ...
Unpacking spinview-qt1 (1.26.0.31) ...
Setting up spinview-qt1-dev (1.26.0.31) ...
Setting up spinview-qt1 (1.26.0.31) ...
ldconfig: /lib/libicuuc.so.56 is not a symbolic link

ldconfig: /lib/libQt5Network.so.5 is not a symbolic link

ldconfig: /lib/libicudata.so.56 is not a symbolic link

ldconfig: /lib/libicui18n.so.56 is not a symbolic link

ldconfig: /lib/libQt5Widgets.so.5 is not a symbolic link

ldconfig: /lib/libQt5XcbQpa.so.5 is not a symbolic link

ldconfig: /lib/libQt5Core.so.5 is not a symbolic link

ldconfig: /lib/libQt5OpenGL.so.5 is not a symbolic link

ldconfig: /lib/libQt5Gui.so.5 is not a symbolic link

ldconfig: /lib/libQt5DBus.so.5 is not a symbolic link

Processing triggers for mime-support (3.64) ...
Processing triggers for desktop-file-utils (0.24-1) ...
Selecting previously unselected package spinupdate1-dev.
(Reading database ... 431768 files and directories currently installed.)
Preparing to unpack spinupdate-1.26.0.31_amd64-dev.deb ...
Unpacking spinupdate1-dev (1.26.0.31) ...
Selecting previously unselected package spinupdate1.
Preparing to unpack spinupdate-1.26.0.31_amd64.deb ...
Unpacking spinupdate1 (1.26.0.31) ...
Setting up spinupdate1-dev (1.26.0.31) ...
Setting up spinupdate1 (1.26.0.31) ...
ldconfig: /lib/libicuuc.so.56 is not a symbolic link

ldconfig: /lib/libQt5Network.so.5 is not a symbolic link

ldconfig: /lib/libicudata.so.56 is not a symbolic link

ldconfig: /lib/libicui18n.so.56 is not a symbolic link

ldconfig: /lib/libQt5Widgets.so.5 is not a symbolic link

ldconfig: /lib/libQt5XcbQpa.so.5 is not a symbolic link

ldconfig: /lib/libQt5Core.so.5 is not a symbolic link

ldconfig: /lib/libQt5OpenGL.so.5 is not a symbolic link

ldconfig: /lib/libQt5Gui.so.5 is not a symbolic link

ldconfig: /lib/libQt5DBus.so.5 is not a symbolic link

Selecting previously unselected package spinnaker.
(Reading database ... 431810 files and directories currently installed.)
Preparing to unpack spinnaker-1.26.0.31_amd64.deb ...
Unpacking spinnaker (1.26.0.31) ...
Selecting previously unselected package spinnaker-doc.
Preparing to unpack spinnaker-doc-1.26.0.31_amd64.deb ...
Unpacking spinnaker-doc (1.26.0.31) ...
Setting up spinnaker (1.26.0.31) ...
Setting up spinnaker-doc (1.26.0.31) ...
Processing triggers for mime-support (3.64) ...
Processing triggers for desktop-file-utils (0.24-1) ...

Would you like to add a udev entry to allow access to USB hardware?
If this is not ran then your cameras may be only accessible by running Spinnaker as sudo.
[Y/n] $ Y
Launching udev configuration script...

This script will assist users in configuring their udev rules to allow
access to USB devices. The script will create a udev rule which will
add FLIR USB devices to a group called flirimaging. The user may also
choose to restart the udev daemon. All of this can be done manually as well.

Adding new members to usergroup flirimaging...
Usergroup flirimaging is empty
To add a new member please enter username (or hit Enter to continue):
$ (my_username)
....
</code></pre>
Follow the instructions.

#### 1.2.1. Modify the USB-FS memory in Linux.
<pre><code>$ vi /etc/default/grub
	GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"
	as 
	GRUB_CMDLINE_LINUX_DEFAULT="quiet splash usbcore.usbfs_memory_mb=1000"
$ update-grub
$ reboot</code></pre>

#### 1.2.2. Increase the receive buffer size
<pre><code>$ vi /etc/sysctl.conf
    net.core.rmem_max=10485760
    net.core.rmem_default=10485760
$ sysctl -p</code></pre>

## 2. Install Spinnaker python module.
### 2.1. Create virtualenv.
<pre><code>$ python3.7 -m venv ./venv
$ source ./venv/bin/activate</code></pre>

### 2.2. Dependencies.
<pre><code>(venv)$ pip install -U numpy</code></pre>
### 2.3. Spinnaker.
<pre><code>(venv)$ pip install spinnaker_python-1.26.0.31-cp37-cp37m-linux_x86_64.whl</code></pre>

## 3. Install python-dependencies.
<pre><code>(venv)$ pip install PyQt5 pyserial construct PyCRC</code></pre>

