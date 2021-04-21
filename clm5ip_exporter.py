#!/usr/bin/python3

import socket
import sys
import time

from prometheus_client import start_http_server
from prometheus_client.core import GaugeMetricFamily, REGISTRY

class Clm5ipCollector(object):
  def __init__(self, target):
    try:
      self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self._socket.connect((target, 10001))
    except ConnectionError as err:
      sys.stderr.write("Could not connect to CLM5IP: {0}\n".format(err))
      exit(2)

    info = self.executeCommand("i").split(";")
    if (info[0] != "CLM5IP"):
      sys.stderr.write("Device did not report as CLM5IP, but instead as '" + info[0] + "'\n")
      exit(3)

    self._outputNames = []
    for i in range(5):
      self._outputNames.append(self.getName("o" + str(i + 1)))
    self._temperatureNames = []
    for i in range(2):
      self._temperatureNames.append(self.getName("t" + str(i + 1)))
    self._analogInNames = []
    for i in range(2):
      self._analogInNames.append(self.getName("ain" + str(i + 1)))
    self._digitalInNames = []
    for i in range(4):
      self._digitalInNames.append(self.getName("din" + str(i + 1)))

  def collect(self):
    activePower = GaugeMetricFamily('clm5ip_active_power_watts', 'Active power P', labels=["output"])
    apparentPower = GaugeMetricFamily('clm5ip_apparent_power_va', 'Apparent power S', labels=["output"])
    reactivePower = GaugeMetricFamily('clm5ip_reactive_power_var', 'Reactive power Q', labels=["output"])
    voltage = GaugeMetricFamily('clm5ip_voltage_volts', 'Voltage V', labels=["output"])
    current = GaugeMetricFamily('clm5ip_current_amperes', 'Current I', labels=["output"])
    powerState = GaugeMetricFamily('clm5ip_power_state', 'Power status (1 = On)', labels=["output"])
    temperature = GaugeMetricFamily('clm5ip_temperature_celsius', 'Temperature', labels=["input"])
    analogIn = GaugeMetricFamily('clm5ip_analog_in_ratio', 'Analog input', labels=["input"])
    digitalIn = GaugeMetricFamily('clm5ip_digital_in_status', 'Digital input (1 = On)', labels=["input"])

    data = self.executeCommand("get data").replace(",", ".").split(";")
    if len(data) != 40:
      sys.stderr.write("Received invalid data, expected 40 fields but got " + str(len(data)) + "\n")
      return

    for i in range(5):
      activePower.add_metric([self._outputNames[i]], float(data[(i * 6) + 0]))
      apparentPower.add_metric([self._outputNames[i]], float(data[(i * 6) + 1]))
      reactivePower.add_metric([self._outputNames[i]], float(data[(i * 6) + 2]))
      voltage.add_metric([self._outputNames[i]], float(data[(i * 6) + 3]))
      current.add_metric([self._outputNames[i]], float(data[(i * 6) + 4]))
      powerState.add_metric([self._outputNames[i]], int(data[(i * 6) + 5]))

    for i in range(2):
      temperature.add_metric([self._temperatureNames[i]], float(data[30 + i]))

    for i in range(2):
      analogIn.add_metric([self._analogInNames[i]], float(data[32 + i]) / 100.0)

    for i in range(4):
      digitalIn.add_metric([self._digitalInNames[i]], int(data[34 + i]))

    yield activePower
    yield apparentPower
    yield reactivePower
    yield voltage
    yield current
    yield powerState
    yield temperature
    yield analogIn
    yield digitalIn

  def getName(self, module):
    ret = self.executeCommand("gn " + module).split(";")
    return ret[0]

  def executeCommand(self, command):
    self._socket.send((command + "\r\n").encode())
    buffer = bytearray()
    while True:
      chunk = self._socket.recv(16)
      buffer.extend(chunk)
      if b'\n' in chunk or not chunk:
        break
    firstline = buffer[:buffer.find(b'\r\n')].decode()
    if firstline == "" or "unknown" in firstline:
      sys.stderr.write("Command '" + command + "' could not be executed\n")
      return ""

    return firstline

def main():
  try:
    if len(sys.argv) < 2:
      sys.stderr.write("Usage: clm5ip_exporter.py 192.168.0.162\n")
      exit(1)
    REGISTRY.register(Clm5ipCollector(sys.argv[1]))
    start_http_server(9819)
    while True:
      time.sleep(1)
  except KeyboardInterrupt:
    print(" Interrupted")
    exit(0)

if __name__ == "__main__":
  main()
