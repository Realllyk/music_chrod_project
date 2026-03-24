"""
Windows 系统音频采集 Agent
使用 WASAPI loopback 抓取系统正在播放的音频

依赖安装（在 Windows 上运行）：
pip install pyaudiowpatch requests

使用方法：
python agent.py [--backend URL] [--output DIR]
"""

import os
import sys
import time
import json
import wave
import argparse
import requests
from datetime import datetime
from pathlib import Path

try:
    import pyaudiowpatch as pyaudio
except ImportError:
    print("错误：请先安装 pyaudiowpatch")
    print("运行：pip install pyaudiowpatch")
    sys.exit(1)


# ============================================================================
# 配置
# ============================================================================

DEFAULT_BACKEND = "http://127.0.0.1:5000"
DEFAULT_RECORDINGS_DIR = "./recordings"
POLL_INTERVAL = 2  # 秒
CHUNK = 1024
FORMAT = pyaudio.paInt16
SAMPLE_WIDTH = 2  # 16-bit = 2 bytes


# ============================================================================
# 录音器类
# ============================================================================

class LoopbackRecorder:
    """WASAPI Loopback 录音器"""
    
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.frames = []
        self.sample_rate = None
        self.channels = None
        self.device_name = None
        self.is_recording = False
    
    def list_loopback_devices(self):
        """列出所有可用的 loopback 设备"""
        devices = []
        try:
            wasapi_info = self.p.get_host_api_info_by_type(pyaudio.paWASAPI)
            for i in range(self.p.get_device_count()):
                device_info = self.p.get_device_info_by_index(i)
                if device_info.get('hostApi') == wasapi_info['index']:
                    # 检查是否是 loopback 设备
                    if device_info.get('maxInputChannels', 0) > 0:
                        devices.append({
                            'index': i,
                            'name': device_info['name'],
                            'channels': device_info['maxInputChannels'],
                            'sample_rate': int(device_info['defaultSampleRate'])
                        })
        except Exception as e:
            print(f"枚举设备失败: {e}")
        return devices
    
    def open_default_loopback(self):
        """打开默认的 loopback 设备"""
        try:
            # 获取默认的 WASAPI loopback 设备
            default_speakers = self.p.get_default_wasapi_loopback()
            
            self.sample_rate = int(default_speakers["defaultSampleRate"])
            self.channels = int(default_speakers["maxInputChannels"])
            self.device_name = default_speakers["name"]
            
            print(f"✓ 使用设备: {self.device_name}")
            print(f"  采样率: {self.sample_rate} Hz")
            print(f"  声道数: {self.channels}")
            
            self.stream = self.p.open(
                format=FORMAT,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=default_speakers["index"],
                frames_per_buffer=CHUNK,
            )
            return True
            
        except Exception as e:
            print(f"✗ 打开 loopback 设备失败: {e}")
            return False
    
    def start(self):
        """开始录制"""
        self.frames = []
        self.is_recording = True
        if self.stream is None:
            if not self.open_default_loopback():
                return False
        return True
    
    def read_frame(self):
        """读取一帧音频数据"""
        if self.stream and self.is_recording:
            try:
                data = self.stream.read(CHUNK, exception_on_overflow=False)
                self.frames.append(data)
                return True
            except Exception as e:
                print(f"读取音频数据失败: {e}")
                return False
        return False
    
    def stop(self):
        """停止录制"""
        self.is_recording = False
    
    def get_duration(self):
        """获取录制时长（秒）"""
        if self.sample_rate and len(self.frames) > 0:
            return len(self.frames) * CHUNK / self.sample_rate
        return 0
    
    def close(self):
        """关闭资源"""
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
        self.p.terminate()


# ============================================================================
# 文件操作
# ============================================================================

def ensure_dir(path):
    """确保目录存在"""
    os.makedirs(path, exist_ok=True)


def build_session_paths(session_id, recordings_dir):
    """构建会话文件路径"""
    date_part = datetime.now().strftime("%Y%m%d")
    dir_path = os.path.join(recordings_dir, date_part)
    ensure_dir(dir_path)
    wav_path = os.path.join(dir_path, f"{session_id}.wav")
    meta_path = os.path.join(dir_path, f"{session_id}.json")
    return wav_path, meta_path


def write_wav(wav_path, frames, channels, sample_rate):
    """写入 WAV 文件"""
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(sample_rate)
        wf.writeframes(b"".join(frames))
    
    # 获取文件大小
    size = os.path.getsize(wav_path)
    return size


def write_metadata(meta_path, payload):
    """写入元数据文件"""
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


# ============================================================================
# Flask API 客户端
# ============================================================================

class FlaskClient:
    """Flask 后端 API 客户端"""
    
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
    
    def get_active_session(self):
        """获取当前活跃的采集会话"""
        try:
            resp = requests.get(
                f"{self.base_url}/api/capture/active",
                timeout=5
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get('session_id'):
                    return data
            return None
        except requests.exceptions.ConnectionError:
            return None
        except Exception as e:
            print(f"获取活跃会话失败: {e}")
            return None
    
    def register_file(self, payload):
        """向后端注册已保存的文件"""
        try:
            resp = requests.post(
                f"{self.base_url}/api/capture/register-file",
                json=payload,
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                # 如果后端要求上传文件
                if data.get('message') and 'upload-file' in data['message']:
                    return 'upload_required'
            return resp.status_code == 200
        except Exception as e:
            print(f"注册文件失败: {e}")
            return False
    
    def upload_file(self, session_id, file_path):
        """上传 WAV 文件到后端"""
        try:
            with open(file_path, 'rb') as f:
                files = {'audio_file': (os.path.basename(file_path), f, 'audio/wav')}
                data = {'session_id': session_id}
                resp = requests.post(
                    f"{self.base_url}/api/capture/upload-file",
                    files=files,
                    data=data,
                    timeout=60
                )
                if resp.status_code == 200:
                    print("✓ 文件上传成功")
                    return True
                else:
                    print(f"✗ 文件上传失败: {resp.status_code}")
                    return False
        except Exception as e:
            print(f"上传文件失败: {e}")
            return False
    
    def check_should_stop(self, session_id):
        """检查是否应该停止录制"""
        try:
            resp = requests.get(
                f"{self.base_url}/api/capture/active",
                timeout=5
            )
            if resp.status_code != 200:
                return True
            data = resp.json()
            # 如果活跃会话不是当前会话，说明应该停止
            return data.get('session_id') != session_id
        except:
            return False


# ============================================================================
# 主循环
# ============================================================================

def record_session(recorder, client, session_id, recordings_dir):
    """录制一个会话"""
    print(f"\n🎙️ 开始录制会话: {session_id}")
    print("   按 Ctrl+C 或在网页上点击停止来结束录制")
    print("   正在录制...")
    
    start_time = datetime.now()
    
    if not recorder.start():
        print("✗ 启动录制失败")
        return False
    
    # 录制循环
    frame_count = 0
    try:
        while recorder.is_recording:
            if recorder.read_frame():
                frame_count += 1
                # 每秒显示一次进度
                if frame_count % (recorder.sample_rate // CHUNK) == 0:
                    duration = recorder.get_duration()
                    print(f"\r   已录制: {duration:.1f} 秒", end="", flush=True)
            
            # 检查是否应该停止
            if client.check_should_stop(session_id):
                print("\n✓ 收到停止信号")
                break
                
    except KeyboardInterrupt:
        print("\n✓ 用户中断")
    
    recorder.stop()
    end_time = datetime.now()
    
    # 保存文件
    wav_path, meta_path = build_session_paths(session_id, recordings_dir)
    
    print(f"\n📁 保存文件: {wav_path}")
    file_size = write_wav(
        wav_path, 
        recorder.frames, 
        recorder.channels, 
        recorder.sample_rate
    )
    
    duration_sec = recorder.get_duration()
    
    # 构建元数据
    meta = {
        "session_id": session_id,
        "source": "wasapi_loopback",
        "file_name": os.path.basename(wav_path),
        "file_path": os.path.abspath(wav_path),
        "sample_rate": recorder.sample_rate,
        "channels": recorder.channels,
        "sample_width_bytes": SAMPLE_WIDTH,
        "encoding": "pcm16",
        "device_name": recorder.device_name,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "duration_sec": duration_sec,
        "file_size_bytes": file_size,
        "status": "recorded"
    }
    
    # 保存元数据
    write_metadata(meta_path, meta)
    print(f"📄 保存元数据: {meta_path}")
    
    # 向后端注册文件
    print("📤 向后端注册文件...")
    result = client.register_file(meta)
    if result == 'upload_required':
        # 需要上传文件
        print("⏳ 正在上传 WAV 文件...")
        if client.upload_file(session_id, wav_path):
            print("✓ 文件上传成功")
        else:
            print("✗ 文件上传失败（文件保留在本地）")
    elif result:
        print("✓ 文件注册成功")
    else:
        print("✗ 文件注册失败（后端可能离线）")
    
    print(f"\n✅ 录制完成")
    print(f"   时长: {duration_sec:.1f} 秒")
    print(f"   文件大小: {file_size / 1024 / 1024:.2f} MB")
    
    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Windows 系统音频采集 Agent"
    )
    parser.add_argument(
        "--backend", "-b",
        default=DEFAULT_BACKEND,
        help=f"Flask 后端地址 (默认: {DEFAULT_BACKEND})"
    )
    parser.add_argument(
        "--output", "-o",
        default=DEFAULT_RECORDINGS_DIR,
        help=f"录音文件保存目录 (默认: {DEFAULT_RECORDINGS_DIR})"
    )
    parser.add_argument(
        "--list-devices", "-l",
        action="store_true",
        help="列出可用的 loopback 设备"
    )
    parser.add_argument(
        "--standalone", "-s",
        action="store_true",
        help="独立模式（不连接后端，手动开始/停止）"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🎵 Windows 系统音频采集 Agent")
    print("=" * 60)
    
    # 初始化录音器
    recorder = LoopbackRecorder()
    
    # 列出设备
    if args.list_devices:
        print("\n可用的 WASAPI Loopback 设备:")
        devices = recorder.list_loopback_devices()
        if devices:
            for d in devices:
                print(f"  [{d['index']}] {d['name']}")
                print(f"      声道: {d['channels']}, 采样率: {d['sample_rate']} Hz")
        else:
            print("  未找到可用设备")
        recorder.close()
        return
    
    # 独立模式
    if args.standalone:
        print(f"\n📁 录音保存目录: {os.path.abspath(args.output)}")
        print("\n🔴 独立模式 - 按 Enter 开始录制，再按 Enter 停止")
        
        input("按 Enter 开始录制...")
        
        session_id = f"standalone_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()
        
        if not recorder.start():
            print("✗ 启动录制失败")
            recorder.close()
            return
        
        print("🎙️ 正在录制... 按 Enter 停止")
        
        # 在后台线程中录制
        import threading
        
        def record_loop():
            while recorder.is_recording:
                recorder.read_frame()
        
        record_thread = threading.Thread(target=record_loop)
        record_thread.start()
        
        input()  # 等待用户按 Enter
        
        recorder.stop()
        record_thread.join()
        
        end_time = datetime.now()
        
        # 输入文件名
        print("\n请输入录音文件名（直接回车使用默认名称）:")
        custom_name = input("文件名: ").strip()
        
        if custom_name:
            # 使用自定义名称
            if not custom_name.endswith('.wav'):
                custom_name += '.wav'
            wav_path = os.path.join(args.output, custom_name)
        
        print(f"\n📁 保存文件: {wav_path}")
        
        file_size = write_wav(
            wav_path,
            recorder.frames,
            recorder.channels,
            recorder.sample_rate
        )
        
        duration_sec = recorder.get_duration()
        
        meta = {
            "session_id": session_id,
            "source": "wasapi_loopback",
            "file_name": os.path.basename(wav_path),
            "file_path": os.path.abspath(wav_path),
            "sample_rate": recorder.sample_rate,
            "channels": recorder.channels,
            "duration_sec": duration_sec,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "status": "recorded"
        }
        
        write_metadata(meta_path, meta)
        
        print(f"✅ 录制完成: {duration_sec:.1f} 秒, {file_size / 1024 / 1024:.2f} MB")
        recorder.close()
        return
    
    # 正常模式 - 连接后端
    client = FlaskClient(args.backend)
    
    print(f"\n🌐 后端地址: {args.backend}")
    print(f"📁 录音保存目录: {os.path.abspath(args.output)}")
    print(f"\n⏳ 等待采集任务...")
    print("   在网页上点击「开始采集」来启动录制")
    print("   按 Ctrl+C 退出 Agent")
    
    try:
        while True:
            # 轮询后端
            session = client.get_active_session()
            
            if session and session.get('status') in ['ready', 'recording_requested']:
                session_id = session['session_id']
                record_session(recorder, client, session_id, args.output)
                print(f"\n⏳ 继续等待下一个采集任务...")
            else:
                time.sleep(POLL_INTERVAL)
                
    except KeyboardInterrupt:
        print("\n\n👋 Agent 已退出")
    finally:
        recorder.close()


if __name__ == "__main__":
    main()
