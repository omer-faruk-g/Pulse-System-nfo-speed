# PulseSystemInfo.py
# Gelişmiş, hafif ve hızlı sistem izleme uygulaması (CPU, RAM, Disk, Network, Process Listesi)
# PyQt5 + psutil + pyqtgraph kullanıyor
# Kullanım:
#   pip install pyqt5 psutil pyqtgraph
#   python PulseSystemInfo.py

from __future__ import annotations
import sys
import time
import psutil
from collections import deque
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QListWidget, QListWidgetItem, QLineEdit, QComboBox, QSpinBox, QPushButton
from PyQt5.QtCore import QTimer
import pyqtgraph as pg
import shutil

APP_UPDATE_INTERVAL_MS = 1000
MAX_HISTORY = 60

def human_readable_bytes(n):
    step = 1024.0
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    while n >= step and i < len(units) - 1:
        n /= step
        i += 1
    return f"{n:.1f} {units[i]}"

class SystemData:
    def __init__(self):
        self.last_net = psutil.net_io_counters()
        self.last_time = time.time()
        self.cpu_hist = deque(maxlen=MAX_HISTORY)
        self.ram_hist = deque(maxlen=MAX_HISTORY)
        self.net_sent_hist = deque(maxlen=MAX_HISTORY)
        self.net_recv_hist = deque(maxlen=MAX_HISTORY)
        for _ in range(MAX_HISTORY):
            self.cpu_hist.append(0.0)
            self.ram_hist.append(0.0)
            self.net_sent_hist.append(0.0)
            self.net_recv_hist.append(0.0)

    def sample(self):
        now = time.time()
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        net = psutil.net_io_counters()
        elapsed = now - self.last_time if now - self.last_time > 0 else 1.0
        sent_rate = (net.bytes_sent - self.last_net.bytes_sent) / elapsed
        recv_rate = (net.bytes_recv - self.last_net.bytes_recv) / elapsed
        self.last_net = net
        self.last_time = now
        self.cpu_hist.append(cpu)
        self.ram_hist.append(ram)
        self.net_sent_hist.append(sent_rate)
        self.net_recv_hist.append(recv_rate)
        return {"cpu": cpu, "ram": ram, "net_sent": sent_rate, "net_recv": recv_rate}

class ProcessItemWidget(QWidget):
    def __init__(self, name, pid, cpu, mem):
        super().__init__()
        layout = QHBoxLayout()
        self.nameLabel = QLabel(f"{name} (PID {pid})")
        self.cpuBar = QProgressBar(); self.cpuBar.setMaximum(100); self.cpuBar.setValue(int(cpu)); self.cpuBar.setFormat(f"CPU: {cpu:.1f}%")
        self.memBar = QProgressBar(); self.memBar.setMaximum(100); self.memBar.setValue(int(mem)); self.memBar.setFormat(f"RAM: {mem:.1f}%")
        layout.addWidget(self.nameLabel,3); layout.addWidget(self.cpuBar,1); layout.addWidget(self.memBar,1)
        self.setLayout(layout)

class PulseSystemInfoApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pulse System Info")
        self.setGeometry(200,100,1000,600)
        central = QWidget(); self.setCentralWidget(central)
        main_layout = QHBoxLayout(); central.setLayout(main_layout)

        left_frame = QVBoxLayout(); main_layout.addLayout(left_frame,3)
        self.cpu_label = QLabel("CPU: 0%"); self.cpu_bar = QProgressBar(); self.cpu_bar.setMaximum(100)
        self.ram_label = QLabel("RAM: 0%"); self.ram_bar = QProgressBar(); self.ram_bar.setMaximum(100)
        left_frame.addWidget(self.cpu_label); left_frame.addWidget(self.cpu_bar)
        left_frame.addWidget(self.ram_label); left_frame.addWidget(self.ram_bar)

        net_box = QHBoxLayout(); self.net_up_label = QLabel("Up: 0 B/s"); self.net_down_label = QLabel("Down: 0 B/s"); net_box.addWidget(self.net_up_label); net_box.addWidget(self.net_down_label)
        left_frame.addLayout(net_box)

        self.process_list = QListWidget(); left_frame.addWidget(QLabel("Processes:")); left_frame.addWidget(self.process_list,4)

        right_frame = QVBoxLayout(); main_layout.addLayout(right_frame,4)
        pg.setConfigOptions(antialias=True)
        self.cpu_plot = pg.PlotWidget(title="CPU (%)"); self.cpu_plot.setYRange(0,100); self.cpu_curve = self.cpu_plot.plot(pen='w')
        self.ram_plot = pg.PlotWidget(title="RAM (%)"); self.ram_plot.setYRange(0,100); self.ram_curve = self.ram_plot.plot(pen='w')
        self.net_plot = pg.PlotWidget(title="Network (KB/s)"); self.net_plot.addLegend(); self.net_sent_curve = self.net_plot.plot(name='Sent',pen='y'); self.net_recv_curve = self.net_plot.plot(name='Recv',pen='c')
        right_frame.addWidget(self.cpu_plot,1); right_frame.addWidget(self.ram_plot,1); right_frame.addWidget(self.net_plot,1)

        self.data = SystemData(); self.timer = QTimer(); self.timer.setInterval(APP_UPDATE_INTERVAL_MS); self.timer.timeout.connect(self.update); self.timer.start()
        self.update()

    def format_bytes_per_sec(self,bps):
        if bps<1024: return f"{bps:.0f} B/s"
        kb = bps/1024.0; mb = kb/1024.0
        if kb<1024: return f"{kb:.1f} KB/s"
        return f"{mb:.1f} MB/s"

    def update(self):
        sample = self.data.sample(); cpu = sample['cpu']; ram = sample['ram']; sent = sample['net_sent']; recv = sample['net_recv']
        self.cpu_label.setText(f"CPU: {cpu:.1f}%"); self.cpu_bar.setValue(int(cpu))
        self.ram_label.setText(f"RAM: {ram:.1f}%"); self.ram_bar.setValue(int(ram))
        x = list(range(-len(self.data.cpu_hist)+1,1))
        self.cpu_curve.setData(x,list(self.data.cpu_hist))
        self.ram_curve.setData(x,list(self.data.ram_hist))
        self.net_sent_curve.setData(x,[s/1024.0 for s in self.data.net_sent_hist])
        self.net_recv_curve.setData(x,[r/1024.0 for r in self.data.net_recv_hist])

def main():
    app = QApplication(sys.argv); win = PulseSystemInfoApp(); win.show(); sys.exit(app.exec_())

if __name__=='__main__':
    main()
