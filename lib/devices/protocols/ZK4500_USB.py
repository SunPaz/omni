import sys, usb.core
import usb.util
import time

RQUEST_GET_DESCRIPTOR = 0x06
REQUEST_TYPE_HOST_TO_DEVICE_CLASS = 0x40
REQUEST_TYPE_DEVICE_TO_HOST_STANDARD = 0x80
REQUEST_TYPE_DEVICE_TO_HOST_CLASS = 0xc0

class ZKReader:
	def __init__(self):
		print("Init")
		dev = usb.core.find(idVendor=0x1b55, idProduct=0x0840)
		if dev is None:
			sys.exit("No ZK");

		try:
			if dev.is_kernel_driver_active(0) is True:
				dev.detach_kernel_driver(0)
		except usb.core.USBError as e:
			sys.exit("Kernel driver won't give up control over device: %s" % str(e))

		dev.reset()
		dev.set_configuration()
		self.dev = dev;

	def beep(self):
		""" Toggle beep for one sec """
		ret = self.dev.ctrl_transfer(REQUEST_TYPE_HOST_TO_DEVICE_CLASS, 0xe1, 0x01, 0x02, None, timeout)
		time.sleep(1)
		ret = self.dev.ctrl_transfer(REQUEST_TYPE_HOST_TO_DEVICE_CLASS, 0xe1, 0x00, 0x02, None, timeout)

	def blink(self):
		""" Toggle blink for one sec """
		ret = self.dev.ctrl_transfer(REQUEST_TYPE_HOST_TO_DEVICE_CLASS, 0xe1, 0x01, 0x01, None, timeout)
		time.sleep(1)
		ret = self.dev.ctrl_transfer(REQUEST_TYPE_HOST_TO_DEVICE_CLASS, 0xe1, 0x00, 0x01, None, timeout)

	def begin_capture(self):
		""" Start receiving  """

		""" Capture image """
		ret = self.dev.ctrl_transfer(REQUEST_TYPE_HOST_TO_DEVICE_CLASS, 0xe5, 0x01, 0x00, None, timeout)

		""" Configuration 0 / First Interface / First Endpoint"""
		endpoint = dev[0][(0,0)][0]

		frame = b''

		while 1:
			try:
				data = self.dev.read(endpoint.bEndpointAddress, endpoint.wMaxPacketSize, timeout=timeout)
				if data is not None:
					frame += data

			except usb.core.USBError as e:
					print("Error readin data: %s" % str(e))
					break
			except KeyboardInterrupt:
				print("Closed")
				break;
