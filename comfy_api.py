#!/usr/bin/env/python
# -*- coding=utf-8 -*-

import websocket
import uuid
import json
import requests
import os
import time
import random
from loguru import logger
from confs import confg
from log_utils import CustomLogging
from comfy_utils import (
    find_file_matching_pattern,
    generate_task,
    rename_folder,
    get_desktop,
    delete_file
)


class ImageProcessingClient:
    def __init__(self, server_address="127.0.0.1:8188"):
        self.logger = CustomLogging("app_log")
        self.server_address = server_address
        self.client_id = str(uuid.uuid4())

    def queue_prompt(self, prompt):
        """提交处理请求"""
        data = {"prompt": prompt, "client_id": self.client_id}
        try:
            response = requests.post(f"http://{self.server_address}/prompt", json=data)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"队列请求失败: {e}")
            return None

    def get_image(self, filename, subfolder, folder_type):
        """获取生成的图片"""
        params = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        try:
            response = requests.get(f"http://{self.server_address}/view", params=params)
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            logger.error(f"获取图片失败: {e}")
            return None

    def get_history(self, prompt_id):
        """查询任务历史记录"""
        try:
            response = requests.get(f"http://{self.server_address}/history/{prompt_id}")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"查询历史失败: {e}")
            return None

    def interrupt_prompt(self):
        """中断当前任务"""
        try:
            response = requests.post(f"http://{self.server_address}/interrupt")
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"中断任务失败: {e}")

    def clear_cache(self, unload_models=True, free_memory=True):
        """清理服务器缓存"""
        clear_data = {"unload_models": unload_models, "free_memory": free_memory}
        try:
            response = requests.post(f"http://{self.server_address}/free", json=clear_data)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"清理缓存失败: {e}")

    def get_node_info(self, node_name):
        """获取节点信息"""
        try:
            response = requests.get(f"http://{self.server_address}/object_info/{node_name}")
            response.raise_for_status()
            data = response.json()
            logger.info(data)
            return data
        except requests.RequestException as e:
            logger.error(f"获取节点信息失败: {e}")
            return None

    def save_image(self, dir_, content, filename=None):
        """保存图片到指定目录"""
        if not os.path.exists(dir_):
            logger.warning(f"目录不存在: {dir_}")
            return
        filename =f"{filename}-{int(time.time()*1000)}.png" if filename else f"{uuid.uuid4()}.png"
        with open(os.path.join(dir_, filename), "wb") as f:
            f.write(content)
        logger.success(f"图片已成功保存: {filename}")
        self.logger.info(f"图片已成功保存: {os.path.join(dir_, filename)}")

    def upload_image(self, file_path):
        """上传单张图片"""
        url = f"http://{self.server_address}/upload/image"
        origin_name = os.path.basename(file_path).split(".",1)[0]
        try:
            with open(file_path, 'rb') as file:
                files = {'image': (os.path.basename(file_path), file, 'image/jpeg')}
                response = requests.post(url, files=files)
                response.raise_for_status()
                data = response.json()
                logger.success(f"图片上传成功: {data['name']}")
                return data["name"],origin_name
        except requests.RequestException as e:
            logger.error(f"上传图片失败: {e}")
            return None

    def upload_folder(self, arg):
        """上传文件夹内所有图片"""
        images_list = []
        reuslt = []
        if isinstance(arg, str):
            images_list = list(find_file_matching_pattern(arg, r".*\.(jpg|jpeg|png|JPG|JPEG|PNG)$"))
            if not images_list:
                logger.warning(f"未找到图片: {arg}")
                return reuslt
        elif isinstance(arg, list):
            images_list = arg
        for file in images_list:
            image_name = self.upload_image(file)
            if image_name:
                reuslt.append(image_name)

        logger.success(f"文件夹或图片列表上传成功")
        return reuslt

    def process_images(self, ws, prompt, save_folder):
        """WebSocket 处理图片生成"""
        if not os.path.exists(save_folder):
            logger.warning(f"目录不存在: {save_folder}")
            return
        prompt_id = self.queue_prompt(prompt)['prompt_id']

        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    if data['prompt_id'] == prompt_id:
                        if data['node'] is None:
                            logger.success(f"图片已成功保存")
                            break
    def handle_task(self, ws, task, folder):
        """处理单个任务"""
        logger.info(f"开始任务: {task}")
        self.logger.info(f"开始任务: {task}")

        if not os.path.exists(task):
            logger.warning(f"文件夹已被人为删除: {task}")
            return

        open(f"{task}/【已检测到该文件夹，请勿删除】.txt", 'w').close()
        list_ = task.split(folder, 1)[1].strip("\\").split("\\")
        func_name = list_[0].split("-", 1)[0]
        if func_name not in confg['workflow']:
            logger.warning(f"该文件夹层级错误: {task}")
            open(f"{task}/【文件夹层级错误】.txt", 'w').close()
            return

        json_str = open(f"work_flow/{confg['workflow'][func_name]}", "r", encoding="utf-8").read()
        prompt = json.loads(json_str)
        match func_name:
            case "1":
                images_list = self.upload_folder(task)
                if not images_list:
                    return
                prompt["255"]["inputs"]["file_path"] = os.path.join(task, "处理结果")
                for current_tuple in images_list:
                    filename, origin_name = current_tuple
                    prompt["233"]["inputs"]["image"] = filename
                    self.process_images(ws, prompt, task)
                    
            case "2":
                    images_list = list(find_file_matching_pattern(task, r".*\.(jpg|jpeg|png|JPG|JPEG|PNG)$"))
                    if not images_list:
                        logger.warning(f"未找到图片: {task}")
                        return
                    clip_text = os.path.join(task, "clip.txt")
                    if not os.path.exists(clip_text):
                        open(f"{task}/【未找到clip文本】.txt", 'w').close()
                        delete_file(task,"【已检测到该文件夹，请勿删除】.txt")
                        logger.warning(f"未找到clip文本: {clip_text}")
                        return
                    word = open(clip_text, "r", encoding="utf-8").read()
                    output_path = os.path.join(task, "处理结果")
                    for current_pt in images_list:
                        # pt_name = os.path.basename(current_pt).rsplit(".", 1)[0]
                        final_name,pt_name = self.upload_image(current_pt)

                        prompt["29"]["inputs"]["text"] = word
                        prompt["14"]["inputs"]["image"] = final_name
                        prompt["33"]["inputs"]["file_path"] = os.path.join(output_path, f"{pt_name}.png")
                        for _ in range(4):
                            prompt["7"]["inputs"]["noise_seed"] = random.randint(10 ** 14, 10 ** 15 - 1)
                            self.process_images(ws, prompt, task)
            case _:
                logger.warning(f"未定义的工作流: {func_name}")
        # rename_folder(task, f"-已完成-{int(time.time()*1000)}")
        open(f"{task}/【已完成】.txt", 'w').close()
        delete_file(task, "【已检测到该文件夹，请勿删除】.txt")
        rename_folder(task, "-已完成")

    def execute_tasks(self, folder):
        """任务执行主循环"""
        first_folder = tuple((confg["workflow"].keys()))
        # first_folder = ("2",)
        while True:
            task_list = generate_task(folder, r"^(?!.*-已完成).+$",first_folder)
            if not task_list:
                logger.info(f"未检测到任务, 5s 后重试...")
                time.sleep(5)
                continue
            # task_list=[x for x in task_list if r"\\172.16.1.5\74.ai绘图\5-换装工作流" in x or r"\\172.16.1.5\74.ai绘图\6-指定脸模换脸" in x]
            # task_list=[x for x in task_list if  r"\\172.16.1.5\74.ai绘图\6-指定脸模换脸" in x]
            # task_list = [r"\\172.16.1.5\74.ai绘图\6-指定脸模换脸\指定换脸测试"]
            logger.info(f"检测到任务: {task_list}")

            while task_list:
                ws = websocket.WebSocket()
                ws.connect(f"ws://{self.server_address}/ws?clientId={self.client_id}")
                task = task_list.pop()
                self.handle_task(ws, task, folder)
                ws.close()


if __name__ == "__main__":
    ai_folder = os.path.join(get_desktop(), "AI绘图")
    os.makedirs(ai_folder, exist_ok=True)
    log_app = CustomLogging("app_log", os.path.join(ai_folder, "日志.txt"))
    client = ImageProcessingClient()
    client.execute_tasks(r'\\172.16.1.5\全员共享\ai')

