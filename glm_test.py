#! /usr/bin/env/python
# -*- coding=utf-8 -*-
"""
======================模块功能描述=========================    
       @File     : glm_test.py
       @IDE      : PyCharm
       @Author   : 陈虎
       @Date     : 2025/7/30 14:39
       @Desc     : 
=========================================================   
"""
import requests
import base64
import json
from PIL import Image
from io import BytesIO
from zhipuai import ZhipuAI


with open("img.png", 'rb') as f:
    img_base64 = base64.b64encode(f.read()).decode("utf-8")

client = ZhipuAI(api_key="0766e7e1804e47989b8306ca707dc78a.HUJrHyjg1F0AxQV0") # 填写您自己的APIKey
response = client.chat.completions.create(
    # model="glm-4.1v-thinking-flash",
    model="glm-4.5V",
    messages=[
       {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": "排除图片中的各种广告词和标语，找出图片中衣服上的完整印花，为了使视觉模型精准识别到该印花，请直接给出最终以印花描述+印花位置的形式的简洁描述"
          },
          {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{img_base64}"
            }
          }
        ]
      }
    ],
    top_p= 0.7,
    temperature= 0.95,
    max_tokens=16384,
    stream=False
)
# result = response.json()
print(type(response))
print(type(response.choices))
print(response.choices[0].message.content)