#!/usr/bin/env python
# -*- coding:utf-8 -*-
# project : xadmin_server
# filename : request
# author : ly_13
# date : 6/27/2023

import json

import requests
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser
from django.urls.resolvers import ResolverMatch
from django.utils.module_loading import import_string
from rest_framework_simplejwt.authentication import JWTAuthentication
from user_agents import parse

from common.core.auth import GetUserFromAccessToken


def get_request_user(request):
    """
    获取请求user
    (1)如果request里的user没有认证,那么则手动认证一次
    :param request:
    :return:
    """
    user: AbstractBaseUser = getattr(request, 'user', None)
    if user and user.is_authenticated:
        return user
    try:
        user, token = JWTAuthentication().authenticate(request)
    except Exception as e:
        try:
            body = getattr(request, 'request_data', {})
            refresh_token = body.get('refresh')
            if refresh_token:
                token = GetUserFromAccessToken(refresh_token)
                auth_class = import_string(settings.REST_FRAMEWORK.get('DEFAULT_AUTHENTICATION_CLASSES')[0])()
                user = auth_class.get_user(token)
        except Exception as e:
            pass
    return user or AnonymousUser()


def get_request_ip(request):
    """
    获取请求IP
    :param request:
    :return:
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[-1].strip()
        return ip
    ip = request.META.get('REMOTE_ADDR', '') or getattr(request, 'request_ip', None)
    return ip or 'unknown'


def get_request_data(request):
    """
    获取请求参数
    :param request:
    :return:
    """
    request_data = getattr(request, 'request_data', None)
    if request_data:
        return request_data
    if request.META.get('CONTENT_TYPE', '').startswith("multipart/"):
        # 避免字段检查直接报错，axios中form-data数据字段和json字段不统一
        return 'multipart/form-data'
    data: dict = {**request.GET.dict(), **request.POST.dict()}
    if not data:
        try:
            body = request.body
            if body:
                data = json.loads(body)
        except Exception as e:
            pass
        if not isinstance(data, dict):
            data = {'data': data}
    return data


def get_request_path(request, *args, **kwargs):
    """
    获取请求路径
    :param request:
    :param args:
    :param kwargs:
    :return:
    """
    request_path = getattr(request, 'request_path', None)
    if request_path:
        return request_path
    values = []
    for arg in args:
        if len(arg) == 0:
            continue
        if isinstance(arg, str):
            values.append(arg)
        elif isinstance(arg, (tuple, set, list)):
            values.extend(arg)
        elif isinstance(arg, dict):
            values.extend(arg.values())
    if len(values) == 0:
        return request.path
    path: str = request.path
    for value in values:
        path = path.replace('/' + value, '/' + '{id}')
    return path


def get_request_canonical_path(request, ):
    """
    获取请求路径
    :param request:
    :return:
    """
    request_path = getattr(request, 'request_canonical_path', None)
    if request_path:
        return request_path
    path: str = request.path
    resolver_match: ResolverMatch = request.resolver_match
    for value in resolver_match.args:
        path = path.replace(f"/{value}", "/{id}")
    for key, value in resolver_match.kwargs.items():
        if key == 'pk':
            path = path.replace(f"/{value}", f"/{{id}}")
            continue
        path = path.replace(f"/{value}", f"/{{{key}}}")

    return path


def get_browser(request, ):
    """
    获取浏览器名
    :param request:
    :return:
    """
    ua_string = request.META['HTTP_USER_AGENT']
    user_agent = parse(ua_string)
    return user_agent.get_browser()


def get_os(request, ):
    """
    获取操作系统
    :param request:
    :return:
    """
    ua_string = request.META['HTTP_USER_AGENT']
    user_agent = parse(ua_string)
    return user_agent.get_os()


def get_verbose_name(queryset=None, view=None, model=None):
    """
    :param model:
    :param queryset:
    :param view:
    :return:
    """
    try:
        if queryset is not None and hasattr(queryset, 'model'):
            model = queryset.model
        elif view and hasattr(view.get_queryset(), 'model'):
            model = view.get_queryset().model
        elif view and hasattr(view.get_serializer(), 'Meta') and hasattr(view.get_serializer().Meta, 'model'):
            model = view.get_serializer().Meta.model
        if model:
            return getattr(model, '_meta').verbose_name
        else:
            model = queryset.model._meta.verbose_name
    except Exception as e:
        pass
    return model if model else ""


def get_ip_analysis(ip):
    """
    获取ip详细概略
    :param ip: ip地址
    :return:
    """
    data = {
        "continent": "",
        "country": "",
        "province": "",
        "city": "",
        "district": "",
        "isp": "",
        "area_code": "",
        "country_english": "",
        "country_code": "",
        "longitude": "",
        "latitude": ""
    }
    if ip != 'unknown' and ip:
        if getattr(settings, 'ENABLE_LOGIN_ANALYSIS_LOG', True):
            try:
                res = requests.get(url='https://ip.django-vue-admin.com/ip/analysis', params={"ip": ip}, timeout=5)
                if res.status_code == 200:
                    res_data = res.json()
                    if res_data.get('code') == 0:
                        data = res_data.get('data')
                return data
            except Exception as e:
                print(e)
    return data
