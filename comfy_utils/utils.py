#! /usr/bin/env/python
# -*- coding=utf-8 -*-
"""
======================模块功能描述=========================
       @File     : utils.py
       @IDE      : PyCharm
       @Author   : 陈虎
       @Date     : 2024/8/17 上午11:28
       @Desc     :
=========================================================
"""

import os
import re
import shutil
import winreg
import psutil
from loguru import logger
expiration_time = None
def get_desktop():
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders')
    return winreg.QueryValueEx(key, "Desktop")[0]


def find_processes_by_name(name_list, close=True):
    if isinstance(name_list, str):
        name_list = [name_list]
    for process in psutil.process_iter(['pid', 'name']):
        if process.info['name'].lower() in map(str.lower, name_list):
            proc = psutil.Process(process.info['pid'])
            logger.success(f"进程 {process.info['name']} (PID: {process.info['pid']}) 已找到。")
            if not close:
                return True
            proc.terminate()
            return None
        return None
    return None

def find_file_matching_pattern(directory, pattern=None, flag=False):
    try:
        with os.scandir(directory) as entries:
            for item in entries:
                try:
                    # 如果是文件且非空，则进行后续处理
                    if item.is_file() and item.stat().st_size > 0:
                        # 如果指定了模式并且文件名匹配该模式，则返回文件路径
                        if pattern is None or re.match(pattern, item.name):
                            yield item.path
                    # 如果允许递归搜索子目录且当前条目为目录，则递归调用自身
                    elif flag and item.is_dir():
                        yield from find_file_matching_pattern(item.path, pattern, flag)
                except FileNotFoundError:
                    # 处理文件被删除的情况
                    logger.error(f"文件已被删除: {item.path}")
                except PermissionError:
                    # 处理权限不足的情况
                    logger.error(f"权限不足，无法访问 {item.path}")
                except OSError as e:
                    # 处理其他操作系统错误
                    logger.error(f"访问 {item.path} 时出错: {e}")
    except FileNotFoundError:
        # 处理目录被删除的情况
        logger.error(f"目录 {directory} 不存在")
    except PermissionError:
        # 处理权限不足的情况
        logger.error(f"权限不足，无法访问目录 {directory}")
    except OSError as e:
        # 处理其他操作系统错误
        logger.error(f"访问目录 {directory} 时出错: {e}")
        return set()



def find_folder_matching_pattern(directory_path,current_depth=0, max_depth=1, pattern=None,first_folder = None):
    matching_directories = []

    def scan_directory(dir_path,depth):
        try:
            with os.scandir(dir_path) as entries:
                for entry in entries:
                    # 排除回收站文件夹
                    if entry.is_dir() and entry.name != "#recycle" and entry.name != "处理结果":
                        # 匹配文件夹名称
                        if pattern and not re.match(pattern, entry.name):
                            continue
                        if depth == 0 and first_folder:
                            if not entry.name.startswith(first_folder):
                                continue
                        images = list(
                            find_file_matching_pattern(entry.path, r".*\.(jpg|jpeg|png|JPG|JPEG|PNG)$"))
                        text_files = list(
                            # 排除 clip.txt 文件
                            find_file_matching_pattern(entry.path, r"(?!clip\.txt$).*\.(txt|TXT)$"))
                        if text_files:
                            continue
                        if images:
                            matching_directories.append(entry.path)
                        if depth < max_depth:
                        # 递归调用以继续遍历子目录
                            scan_directory(entry.path,depth+1)
        except OSError as e:
            logger.error(f"访问目录时出错: {dir_path}, 错误: {e}")
    scan_directory(directory_path,current_depth)

    return matching_directories


def rename_folder(old_path, new_name, same_folder=True):
    # 检查文件夹是否存在
    if not os.path.exists(old_path):
        logger.warning(f"文件夹 {old_path} 不存在！")
        return
    try:
        # 重命名文件夹
        if same_folder:
            folder_name = os.path.dirname(old_path)
            file_name = os.path.basename(old_path)
            name_ = file_name + new_name
            new_name = os.path.join(folder_name, name_)
        os.rename(old_path, new_name)
        logger.success(f"文件夹已成功从 {old_path} 重命名为 {new_name}")
    except FileNotFoundError:
        logger.error(f"重命名失败: 源文件夹 {old_path} 未找到。")
    except PermissionError:
        logger.error(f"重命名失败: 权限不足，无法重命名 {old_path}。")
    except OSError as e:
        logger.error(f"重命名失败: 操作系统错误 - {e}")
    except Exception as e:
        logger.error(f"重命名失败: 未知错误 - {e}")



def generate_task(folder,pattern,first_folder=None):
    tasks = []
    try:
        result_pt = find_folder_matching_pattern(folder, pattern=pattern,first_folder=first_folder)
        if not result_pt:
            # logger.warning("【未找符合条件的文件夹】>>>>>>>")
            return
        for current_pt in result_pt:
            if not os.path.exists(current_pt):
                continue
            if os.path.exists(os.path.join(current_pt, '【未找到clip文本】.txt')):
                continue
            # 检查【已完成】标记
            if os.path.exists(os.path.join(current_pt, '【已完成】.txt')):
                continue
            tasks.append(current_pt)

        if tasks:
            tasks.sort(key=lambda x: os.stat(x).st_ctime,reverse=True)
        return tasks
    except Exception as e:
        logger.error(f"生成任务异常:{e}")

# 删除文件的函数
def delete_file(folder_path,file_name):
    file_path = os.path.join(folder_path,file_name)
    try:
        os.remove(file_path)
        logger.success(f"文件 {file_path} 已删除。")
    except FileNotFoundError:
        logger.error(f"文件 {file_path} 不存在。")
    except PermissionError:
        logger.error(f"权限不足，无法删除文件 {file_path}。")
    except OSError as e:
        logger.error(f"删除文件 {file_path} 时出错: {e}")
