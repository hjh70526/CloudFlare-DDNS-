#!/usr/bin/python
# -*- coding: UTF-8 -*-
# Python CloudFlare-DDNS 自动更新脚本
# by hjh
#       ┏┓    ┏┓  + +
#      ┏┛┻━━━━┛┻┓ + +
#      ┃        ┃ + +
#      ┃   ━    ┃ + + + + +
#     ████━████ ┃ + + + + +
#      ┃        ┃ +
#      ┃   ┻    ┃
#      ┃        ┃ + +
#      ┗━┓    ┏━┛
#        ┃    ┃
#        ┃    ┃ + + + +
#        ┃    ┃ Codes are far away from bugs with the animal protecting
#        ┃    ┃ + 神兽保佑,代码bug
#        ┃    ┃
#        ┃    ┃ +
#        ┃    ┗━━━┓ + +
#        ┃        ┣┓
#        ┃       ┏┛
#        ┗┓┓┏━┳┓┏┛+ + + +
#         ┃┫┫ ┃┫┫
#         ┗┻┛ ┗┻┛+ + + +

try:
    # Python3加载外部库
    from urllib.request import urlopen
    from urllib.request import Request
    from urllib.error import URLError
    from urllib.error import HTTPError
    # 噜啦啦。。。
except ImportError:      #若加载错误，识别为Python2
    # Python2加载外部库
    from urllib2 import urlopen
    from urllib2 import Request
    from urllib2 import HTTPError
    from urllib2 import URLError

import json


config_file_name = '/usr/local/bin/cf-ddns.conf'   # 使用绝对路径加载配置文件

with open(config_file_name, 'r') as config_file:
    try:
        config = json.loads(config_file.read())
    except ValueError:
        print('错误：请检查配置文件！')
        exit(0)

if not config['user']['email'] or not config['user']['api_key']:
    print('错误：Cloudflare接口错误，请检查！')
    exit(0)

content_header = {'X-Auth-Email': config['user']['email'],
                  'X-Auth-Key': config['user']['api_key'],
                  'Content-type': 'application/json'}

base_url = 'https://api.cloudflare.com/client/v4/zones/'

public_ipv4 = None
public_ipv6 = None
ip_version = None

try:
    public_ipv4 = urlopen(Request(
        'http://ipv4.icanhazip.com/')).read().rstrip().decode('utf-8')
except URLError as e:
    print('未发现Ipv4地址，尝试寻找Ipv6地址')

try:
    public_ipv6 = urlopen(Request(
        'http://ipv6.icanhazip.com/')).read().rstrip().decode('utf-8')
except URLError as e:
    print('未发现Ipv6地址，将更新Ipv4地址')

if public_ipv4 is None and public_ipv4 is None:
    print('错误：未找到任何IP地址，请检查网络！')
    exit(0)

update = False

for domain in config['domains']:
    # 检查域名
    if not domain['name']:
        print('错误：此域名无效，请检查配置！')
        continue

    # 噜啦啦。。
    if not domain['id']:
        try:
            print(
                '咦？ "{0}" 的zone id不见了耶~嘿嘿'
                '正在向CloudFlare获取'.format(domain['name']))
            zone_id_req = Request(base_url, headers=content_header)
            zone_id_resp = urlopen(zone_id_req)
            for d in json.loads(zone_id_resp.read().decode('utf-8'))['result']:
                if domain['name'] == d['name']:
                    domain['id'] = d['id']
                    print(' "{0}" 的zone id是'
                          ' {1}'.format(domain['name'], domain['id']))
        except HTTPError as e:
            print('错误：无法向CLoudFlare获取zone id {0}'.format(domain['name']))
            print('可能是你的cf-ddns.conf配置错误？也有可能是你的CloudFlare域名解析配置错误。。。')
            continue

    for host in domain['hosts']:
        fqdn = host['name'] + '.' + domain['name']

        if not host['name']:
            print('错误：没有找到解析记录，请检查你的CLoudFlare设置！')
            continue

        if not host['id']:
            print(
                '咦？ "{0}" 的host id不见了耶~嘿嘿'
                '正在向CloudFlare获取'.format(fqdn))
            rec_id_req = Request(
                base_url + domain['id'] + '/dns_records/',
                headers=content_header)
            rec_id_resp = urlopen(rec_id_req)
            parsed_host_ids = json.loads(rec_id_resp.read().decode('utf-8'))
            for h in parsed_host_ids['result']:
                if fqdn == h['name']:
                    host['id'] = h['id']
                    print(' "{0}" 的host id是'
                          ' {1}'.format(fqdn, host['id']))

        for t in host['types']:
            if t not in ('A', 'AAAA'):
                print('错误：错误的域名解析记录类型，必须是A或AAAA，你的记录类型是: {0}'.format(t))
                continue
            elif t == 'A':
                if public_ipv4:
                    public_ip = public_ipv4
                    ip_version = 'ipv4'
                else:
                    print('未发现Ipv4地址，，因此无法添加A解析记录')
                    continue
            elif t == 'AAAA':
                if public_ipv6:
                    public_ip = public_ipv6
                    ip_version = 'ipv6'
                else:
                    print('没有找到Ipv6地址，因此无法添加AAAA解析记录')
                    continue

            # 若IP变化，更新IP解析
            if host[ip_version] != public_ip:
                try:
                    if not t:	
                        raise Exception

                    data = json.dumps({
                        'id': host['id'],
                        'type': t,
                        'name': host['name'],
                        'content': public_ip
                    })
                    url_path = '{0}{1}{2}{3}'.format(base_url,
                                                     domain['id'],
                                                     '/dns_records/',
                                                     host['id'])
                    update_request = Request(
                        url_path,
                        data=data.encode('utf-8'),
                        headers=content_header)
                    update_request.get_method = lambda: 'PUT'
                    update_res_obj = json.loads(
                        urlopen(update_request).read().decode('utf-8'))
                    if update_res_obj['success']:
                        update = True
                        host[ip_version] = public_ip
                        print('更新成功 (type: {0}, fqdn: {1}'
                              ', ip: {2})'.format(t, fqdn, public_ip))
                except (Exception, HTTPError) as e:
                    print('哎？更新出错了，可能是网络问题？若多次出错，可能是你的CloudFlare API密钥错误哦！ (type: {0}, fqdn: {1}'
                          ', ip: {2})'.format(t, fqdn, public_ip))

if update:
    print('更新成功啦～')
    with open(config_file_name, 'w') as config_file:
        json.dump(config, config_file, indent=1, sort_keys=True)
else:
    print('IP地址未更换，无需更新～')
# 撸啦啦……皮一下很开森…
