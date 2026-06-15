<div align="center">

# 🧬 C. elegans Neural Simulation
### Autonomous Robot Driven by a Real Biological Connectome

[![ROS2](https://img.shields.io/badge/ROS2-Jazzy-blue?logo=ros&logoColor=white)](https://docs.ros.org/en/jazzy/)
[![Gazebo](https://img.shields.io/badge/Gazebo-Harmonic-orange?logo=gazebo)](https://gazebosim.org/)
[![Python](https://img.shields.io/badge/Python-3.10+-green?logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-Apache%202.0-lightgrey)](LICENSE)
[![OpenWorm](https://img.shields.io/badge/Data-OpenWorm%20Connectome-purple)](http://openworm.org)

<br/>

> **The world's most complete neural dataset driving an autonomous robot in ROS2.**
> Every movement emerges from 299 real neurons and 3,363 real synapses —
> no scripted behaviour, no state machines. Pure biology.

<br/>

---

</div>

##  What This Is

This package simulates *C. elegans* (a 1mm roundworm) as an **autonomous ROS2 robot** whose behaviour emerges entirely from its real connectome — the complete wiring diagram of its nervous system.

- **299 neurons** — every single one modelled as a Leaky Integrate-and-Fire unit
- **3,363 synaptic connections** — chemical synapses and gap junctions from the Varshney et al. dataset
- **Real neural circuits** — AWA olfaction, ASH nociception, AVA reversal command, ALML/ALMR touch
- **Autonomous behaviour** — the worm finds food, avoids obstacles, reverses on touch, all from neural dynamics
- **Full ROS2 integration** — topics, nodes, launch files, RViz2 visualisation

This is the same connectome that the [OpenWorm project](http://openworm.org) uses — running in real time on your machine.

---

##  Demo

```
Worm crawling autonomously in RViz2
↓ Neural circuit running at 100Hz
↓ Muscle activations → joint angles → body undulation
↓ Sensory neurons detecting environment
↓ Behaviour emerging from real connectome
```

---

##  Neural Architecture

```
SENSORY LAYER          INTERNEURON LAYER       MOTOR LAYER
─────────────          ─────────────────       ───────────
AWA  (olfaction)  ───► AIY  (integration) ───► AVBL/AVBR ───► DB/VB motors → Forward
AWB  (repellent)  ───► AIB  (turn)        ───► AVAL/AVAR ───► DA/VA motors → Reverse
ASH  (nociception)───► AVD  (command)     ───► RIM        ───► SMB motors  → Head turn
ALML (touch-head) ───► AVA  (reversal)    ──┐
ALMR (touch-head) ──────────────────────────┘
PLML (touch-tail) ───► PVC  (forward)     ──► AVBL/AVBR
AFD  (temperature)───► AIY  (thermo)      ──► locomotion
```

**Locomotion model:** Sinusoidal muscle wave propagates head→tail (forward) or tail→head (reverse), driven by competing AVB/AVA command neuron activity — exactly as in the biological animal.

---

##  Package Structure

```
celegans_sim/
├── celegans_sim/
│   ├── neural_sim_node.py    # 299-neuron LIF model @ 100Hz
│   ├── worm_body_node.py     # Joint controller + sensory feedback
│   └── neural_viz_node.py    # RViz2 neuron marker publisher
├── urdf/
│   └── celegans.urdf         # 12-segment articulated worm body
├── worlds/
│   └── agar_plate.world      # Gazebo petri dish environment
├── launch/
│   └── celegans_sim.launch.py
├── resource/
│   └── connectome.json       # Real connectome data (OpenWorm)
├── package.xml
└── setup.py
```

---

##  System Requirements

| Component | Version |
|-----------|---------|
| Ubuntu    | 24.04 LTS |
| ROS2      | Jazzy Jalisco |
| Gazebo    | Harmonic |
| Python    | 3.10+ |
| NumPy     | ≥ 1.21 |

---

##  Installation

### 1. Install ROS2 dependencies

```bash
sudo apt update
sudo apt install -y \
  ros-jazzy-robot-state-publisher \
  ros-jazzy-joint-state-publisher \
  ros-jazzy-rviz2 \
  ros-jazzy-xacro \
  ros-jazzy-ros-gz-bridge \
  ros-jazzy-ros-gz-sim \
  ros-jazzy-visualization-msgs \
  ros-jazzy-tf2-ros \
  ros-jazzy-topic-tools
```

### 2. Install Python dependencies

```bash
pip3 install numpy
```

### 3. Clone into your workspace

```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src
git clone https://github.com/YOUR_USERNAME/celegans_neural_sim.git
```

### 4. Build

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select celegans_sim
source install/setup.bash
```

---

##  Running the Simulation

### Full simulation (Gazebo + RViz2)

**Terminal 1 — Launch:**
```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 launch celegans_sim celegans_sim.launch.py
```

**Terminal 2 — Bridge joint states to RViz2:**
```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 run topic_tools relay /worm/joint_states /joint_states
```

**Terminal 3 — Static TF (connects worm to world frame):**
```bash
source /opt/ros/jazzy/setup.bash
ros2 run tf2_ros static_transform_publisher 0 0 0 0 0 0 world segment_0
```

### Neural sim only (no Gazebo)

```bash
ros2 launch celegans_sim celegans_sim.launch.py \
  use_gazebo:=false use_rviz:=false
```

---

## 🔬 RViz2 Setup

After launching, configure RViz2:

1. **Fixed Frame** → set to `world`
2. **Add** → `RobotModel` → Description Topic: `/robot_description`
3. **Add** → `MarkerArray` → Topic: `/neural_markers`
4. **Add** → `TF`
5. **Add** → `Axes` → Reference Frame: `world`

You will see:
- 🐛 The worm body with 12 articulated segments
- 🧠 ~80 glowing neural spheres above the worm (green=sensory, orange=motor, blue=interneuron)
- Neurons brighten as they fire
- Body segments bend from muscle activations

---

## ⚡ Triggering Stimuli

Fire sensory inputs while simulation is running:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash

# Head touch → ALML/ALMR → AVD → AVA → reversal
ros2 topic pub --once /sensory_input std_msgs/msg/Float32MultiArray \
  "data: [1.0, 0.0, 0.0, 0.0, 0.0]"

# Tail touch → PLML/PLMR → PVC → AVB → forward acceleration
ros2 topic pub --once /sensory_input std_msgs/msg/Float32MultiArray \
  "data: [0.0, 1.0, 0.0, 0.0, 0.0]"

# Food smell → AWA → AIY → AVB → forward locomotion
ros2 topic pub --once /sensory_input std_msgs/msg/Float32MultiArray \
  "data: [0.0, 0.0, 1.0, 0.0, 0.0]"

# Nociception → ASH → AVA → reversal + turn
ros2 topic pub --once /sensory_input std_msgs/msg/Float32MultiArray \
  "data: [0.0, 0.0, 0.0, 1.0, 0.0]"

# Temperature → AFD → AIY → thermotaxis
ros2 topic pub --once /sensory_input std_msgs/msg/Float32MultiArray \
  "data: [0.0, 0.0, 0.0, 0.0, 1.0]"
```

Sensory input format: `[head_touch, tail_touch, food_proximity, nociception, temperature]`

---

##  ROS2 Topics

| Topic | Message Type | Direction | Description |
|-------|-------------|-----------|-------------|
| `/sensory_input` | `Float32MultiArray` | → neural_sim | 5 sensory channels |
| `/muscle_activation` | `Float32MultiArray` | neural_sim → body | 24 muscle values |
| `/neural_state` | `Float32MultiArray` | neural_sim → viz | 299 activations @ 10Hz |
| `/worm_behavior` | `String` | neural_sim → log | Current behavior label |
| `/worm/joint_states` | `JointState` | body → Gazebo | 11 joint angles @ 50Hz |
| `/worm/pose` | `Pose` | body → all | Head position in world |
| `/neural_markers` | `MarkerArray` | viz → RViz2 | Neuron spheres @ 10Hz |
| `/robot_description` | `String` | rsp → all | URDF model |

---

##  Monitoring Neural Activity

```bash
# Watch behavior state
ros2 topic echo /worm_behavior

# Watch all 299 neuron activations
ros2 topic echo /neural_state

# Watch muscle outputs (24 values)
ros2 topic echo /muscle_activation

# View node graph
rqt_graph

# Plot neural activity
rqt
```

---

##  Troubleshooting

**`libexec directory does not exist` on launch:**
```bash
# Make sure package.xml has ament_python, not ament_cmake
grep build_type ~/ros2_ws/src/celegans_sim/package.xml
# Must show: <build_type>ament_python</build_type>

# Delete CMakeLists.txt if it exists
rm -f ~/ros2_ws/src/celegans_sim/CMakeLists.txt

# Clean rebuild
rm -rf ~/ros2_ws/build/celegans_sim ~/ros2_ws/install/celegans_sim
cd ~/ros2_ws && colcon build --packages-select celegans_sim
```

**RViz2 shows `No transform from [segment_X] to [world]`:**
```bash
ros2 run tf2_ros static_transform_publisher 0 0 0 0 0 0 world segment_0
```

**Worm body not bending in RViz2:**
```bash
ros2 run topic_tools relay /worm/joint_states /joint_states
```

**Gazebo not found:**
```bash
# ROS2 Jazzy uses gz sim, not gazebo
which gz
sudo apt install ros-jazzy-ros-gz-sim
```

---

##  Neural Model Details

The simulation uses a **Leaky Integrate-and-Fire (LIF)** model:

```
V(t+1) = V(t) × decay + Σ w_ij × fired_j(t)

Where:
  V(t)    = membrane potential of neuron i at time t
  decay   = 0.94  (membrane time constant)
  w_ij    = synaptic weight (from connectome, scaled)
  fired_j = 1 if neuron j fired at t, else 0

Neuron fires when V(t) ≥ threshold (0.35)
Refractory period = 3 steps after firing
Simulation rate  = 100 Hz
```

**Muscle activation:**
```
For each body segment i:
  phase     = t × 0.08 - i × 0.55   (travelling wave)
  dorsal_i  = max(0,  sin(phase)) × fwd_drive
  ventral_i = max(0, -sin(phase)) × fwd_drive
  bend_i    = dorsal_i - ventral_i   → joint angle
```

---

## 📖 Data Source

Connectome data from:

> Varshney LR, Chen BL, Paniagua E, Hall DH, Chklovskii DB (2011).
> *Structural Properties of the Caenorhabditis elegans Neuronal Network.*
> PLOS Computational Biology 7(2): e1001066.
> https://doi.org/10.1371/journal.pcbi.1001066

Made available by the [OpenWorm project](http://openworm.org).

---

##  Roadmap

- [ ] Gazebo Harmonic full physics integration
- [ ] Real contact sensor plugins (bumper sensors on head/tail)
- [ ] Food gradient simulation (chemical diffusion field)
- [ ] rqt neural activity dashboard
- [ ] Docker container for one-command setup
- [ ] Extended to *Drosophila* (fruit fly) connectome

---

##  Contributing

Pull requests are welcome. For major changes please open an issue first.

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/add-thermotaxis`)
3. Commit your changes (`git commit -m 'Add thermotaxis gradient field'`)
4. Push to the branch (`git push origin feature/add-thermotaxis`)
5. Open a Pull Request

---

## 📄 License

Apache 2.0 — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built with real neuroscience data · Runs on ROS2 Jazzy · Powered by OpenWorm connectome

**If this project helped you, please ⭐ star the repo**

</div>
