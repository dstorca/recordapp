from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon

from PyQt5.QtWidgets import (
    QWidget,
    QDesktopWidget,
    QGridLayout,
    QPushButton,
    QLabel,
    QFileDialog, QGroupBox, QHBoxLayout, QVBoxLayout,
)
from pynput.keyboard import Listener, Key
from AudioRecorder import AudioRecorder
from ScreenRecorder import ScreenReader

import moviepy.editor as mpe
import threading
import time
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.join(BASE_DIR, "server")
sys.path.append(SERVER_DIR)
import server


class AudioResolutionApp(QWidget):
    def __init__(self):
        super().__init__()
        self.is_recording = False
        self.screen_recorder = ScreenReader()
        self.audio_recorder = AudioRecorder()
        self.record_shortcut = Key.f2  # default record shortcut is F2
        self.output_file_name = None
        self.file_name = None
        self.init_ui()

    def init_ui(self):
        """
        Initialize Application UI
        """
        WIDTH = 600
        HEIGHT = 300
        self.setWindowTitle("Auido Resolution App")
        self.position_to_center()
        self.resize(WIDTH, HEIGHT)

        # 녹화하기 버튼
        # self.record_btn = QPushButton("녹화하기")
        self.record_btn = QPushButton(self)
        self.record_btn.setStyleSheet('QPushButton::hover { background-color: #C3C3C3 } QPushButton { border: none; }')
        self.record_btn.setFixedSize(60, 60)
        self.record_btn.setToolTip("녹화하기")
        self.record_btn.setIcon(QIcon('./icon/record.svg'))
        self.record_btn.setIconSize(QSize(40, 40))
        self.record_btn.clicked.connect(self.start_record)
        self.record_btn.move(0, 0)

        # 마이크 선택 버튼
        self.mic_setting_btn = QPushButton(self)
        self.mic_setting_btn.setStyleSheet('QPushButton::hover { background-color: #C3C3C3 } QPushButton { border: none; }')
        self.mic_setting_btn.setFixedSize(60, 60)
        self.mic_setting_btn.setToolTip("마이크 설정하기")
        self.mic_setting_btn.setIcon(QIcon('./icon/mic.svg'))
        self.mic_setting_btn.setIconSize(QSize(40, 40))
        self.mic_setting_btn.move(58, 0)


        # 저장된 폴더 열기
        # self.file_open_btn = QPushButton("저장된 폴더 열기")
        self.file_open_btn = QPushButton(self)
        self.file_open_btn.setFixedSize(60, 60)
        self.file_open_btn.setStyleSheet('QPushButton::hover { background-color: #C3C3C3 } QPushButton { border: none }')
        self.file_open_btn.setToolTip("저장 폴더 열기")
        self.file_open_btn.setIcon(QIcon('./icon/folder.svg'))
        self.file_open_btn.setIconSize(QSize(40, 40))
        self.file_open_btn.clicked.connect(self.open_last_created_directory)
        self.file_open_btn.move(118, 0)

        # self.convert_rate_label = QLabel("변환율 나타내기")
        self.setFixedWidth(600)
        self.setFixedHeight(300)

        key_pressed_thread = threading.Thread(
            target=self.key_pressed_listener
        )  # 단축키 이벤트 리스너를 위한 쓰레드
        key_pressed_thread.daemon = True
        key_pressed_thread.start()

        self.show()  # UI 초기화가 끝나면 Application 보여주기

    def position_to_center(self):
        """
        move program's position to center
        """
        qr = self.frameGeometry()  # Get gui window's position and size
        cp = (
            QDesktopWidget().availableGeometry().center()
        )  # Get the center position of the monitor screen
        qr.moveCenter(cp)  # move the gui window position to center
        self.move(qr.topLeft())

    def select_file_location(self):
        """
        녹화하기 버튼을 눌렀을 때 저장할 파일 위치 선택하도록 하는 메소드
        """
        options = QFileDialog.Options() | QFileDialog.DontUseNativeDialog
        self.file_name = QFileDialog.getSaveFileName(
            None, "저장될 파일 위치", "", "avi Files (*.avi)", "", options=options
        )[0]
        self.output_file_name = self.file_name + ".avi"
        self.screen_recorder.file_name = self.file_name + \
            "temp.avi"  # 녹음 파일(임시 파일)명 설정
        self.audio_recorder.file_name = self.file_name + \
            "temp.wav"  # 녹화 파일(임시 파일)명 설정

    def press_record_shortcut(self, key):
        if key == self.record_shortcut:
            print("F2 is clicked")
            self.record_btn.click()

    def set_is_recording(self):
        self.is_recording = not self.is_recording
        self.screen_recorder.is_recording = not self.screen_recorder.is_recording
        self.audio_recorder.is_recording = not self.audio_recorder.is_recording

        if self.is_recording:
            self.record_btn.setText("녹화종료")
        else:
            self.record_btn.setText("녹화하기")

    def start_record(self):
        self.set_is_recording()

        if self.is_recording:
            self.select_file_location()
            self.showMinimized()  # 애플리케이션 창 최소화 하기
            time.sleep(1)  # 창이 최소화되는동안 1초간 정지

            screen_record_thread = threading.Thread(
                target=self.screen_recorder.screen_record
            )
            screen_record_thread.daemon = True
            audio_record_thread = threading.Thread(
                target=self.audio_recorder.audio_record
            )
            audio_record_thread.daemon = True

            screen_record_thread.start()  # 녹화 시작
            audio_record_thread.start()  # 녹음 시작
            print("녹화 및 녹음중")
        else:
            print("딥러닝 변환 부분")
            self.showNormal()  # 최소화된 애플리케이션 창 다시 보여주기
            self.convert_audio_to_super_resolution()  # 딥러닝으로 변환하는 로직 부분
            merge_thread = threading.Thread(target=self.merge_audio_and_video)
            merge_thread.daemon = True
            merge_thread.start()

    def convert_audio_to_super_resolution(self):
        print("변환을 시작합니다...")
        original_file_name = self.audio_recorder.file_name[self.audio_recorder.file_name.rfind('/') + 1:]
        server.audio_resolution(original_file_name)

    def open_last_created_directory(self):
        if self.output_file_name:
            last_idx = self.output_file_name.rfind("/")
            directory_path = self.output_file_name[:last_idx]
            directory_path = os.path.realpath(directory_path)
            os.startfile(directory_path)
        else:
            os.startfile(BASE_DIR)

    def key_pressed_listener(self):
        """
        녹화 버튼 단축키 이벤트 리스너
        애플리케이션이 켜지면 쓰레드로 계속 이벤트가 발생(F2 버튼을 누르는지)하는지 주시하고 있다가
        F2가 눌리면 press_record_shortcut 함수 실행
        """
        with Listener(on_press=self.press_record_shortcut) as listener:
            listener.join()

    def merge_audio_and_video(self):
        sc_file_name = self.screen_recorder.file_name
        # ad_file_name = self.audio_recorder.file_name # 원본 오디오 파일 이름
        ad_file_name = self.audio_recorder.file_name + "..pr.wav"  # 딥러닝 결과 오디오 파일 이름
        output_file_name = self.output_file_name

        # print(self.audio_recorder.file_name)
        audio_clip = mpe.AudioFileClip(ad_file_name)
        video_clip = mpe.VideoFileClip(sc_file_name)
        new_audio_clip = mpe.CompositeAudioClip(
            [audio_clip])  # 녹화된 Video file 객체 얻기
        # print('new_audio_clip' + new_audio_clip)
        video_clip.audio = new_audio_clip  # Video file의 audio를 새로 쓰기
        video_clip.write_videofile(
            output_file_name, codec="png")  # 최종적인 Video file을 쓰기

        # 녹화 파일 삭제
        os.remove(self.file_name + "temp.wav")
        os.remove(self.file_name + "temp.avi")
        os.remove(self.audio_recorder.file_name + "..pr.wav")
        os.remove(self.audio_recorder.file_name + "..pr.png")
        os.remove(self.audio_recorder.file_name + "..lr.wav")
        os.remove(self.audio_recorder.file_name + "..lr.png")
        os.remove(self.audio_recorder.file_name + "..hr.wav")
        os.remove(self.audio_recorder.file_name + "..hr.png")

        print("merge success")