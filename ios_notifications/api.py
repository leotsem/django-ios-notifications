# -*- coding: utf-8 -*-

from django.http import HttpResponseNotAllowed, QueryDict
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from django.contrib.auth.models import User
from django.utils.decorators import method_decorator

from ios_notifications.models import Device
from ios_notifications.forms import DeviceForm
from ios_notifications.decorators import api_authentication_required
from ios_notifications.http import HttpResponseNotImplemented, JSONResponse
import simplejson as json


class BaseResource(object):
	"""
	The base class for any API Resources.
	"""
	allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

	@method_decorator(api_authentication_required)
	@csrf_exempt
	def route(self, request, **kwargs):
		method = request.method
		if method in self.allowed_methods:
			if hasattr(self, method.lower()):
				if method == 'PUT':
					request.PUT = QueryDict(request.raw_post_data).copy()
				return getattr(self, method.lower())(request, **kwargs)

			return HttpResponseNotImplemented()

		return HttpResponseNotAllowed(self.allowed_methods)


class DeviceResource(BaseResource):
	"""
	The API resource for ios_notifications.models.Device.

	Allowed HTTP methods are GET, POST and PUT.
	"""
	allowed_methods = ('GET', 'POST', 'PUT', 'DELETE')

	def get(self, request, **kwargs):
		"""
		Returns an HTTP response with the device in serialized JSON format.
		The device token and device service are expected as the keyword arguments
		supplied by the URL.

		If the device does not exist a 404 will be raised.
		"""
		device = get_object_or_404(Device, **kwargs)
		return JSONResponse(device)

	def post(self, request, **kwargs):
		"""
		Creates a new device or updates an existing one to `is_active=True`.
		Expects two non-options POST parameters: `token` and `service`.
		"""
		params = json.loads(request.raw_post_data)
		devices = Device.objects.filter(token=params['token'],
										service__id=int(params['service']))
		if params['token'] and params['service']:

			if devices.exists():

				device = devices.get()
				device.is_active = True

				if 'uid' in request.GET:

					try:
						u = User.objects.get(id=request.GET.get('uid'))
						device.users.clear()
						device.users.add(u)

					except Exception:
						pass

				device.save()
				return JSONResponse(device)

			else:

				device = Device()
				device.is_active = True
				device.token = params['token']
				device.service_id = int(params['service'])
				device.save()

				if 'uid' in request.GET:
					try:
						u = User.objects.get(id=request.GET.get('uid'))
						device.users.add(u)
					except Exception:
						pass

				return JSONResponse(device)

	def delete(self, request, **kwargs):
		"""
		Deletes an existing device
		"""
		try:

			device = Device.objects.get(**kwargs)
			device.is_active = False
			device.save()

			return JSONResponse(device)

		except Device.DoesNotExist:
			return JSONResponse({'error': 'Device with token %s and service %s does not exist' %
								(kwargs['token'], kwargs['service__id'])}, status=400)


class Router(object):
	"""
	A simple class for handling URL routes.
	"""
	def __init__(self):
		self.device = DeviceResource().route

routes = Router()
