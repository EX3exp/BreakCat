import sys
from os.path import isfile, exists
from os.path import join as join_
from os.path import split as split_
from PyQt5.QtWidgets import QApplication, QMainWindow, QComboBox, QFileDialog, QMessageBox
from PyQt5 import uic
from PyQt5.QtGui import QIcon, QCursor
from PyQt5.QtCore import QTranslator, QStringListModel
import pickle
from functools import partial
from os import remove, rename, listdir, makedirs
from chardet import detect
from PyQt5.QtCore import Qt 
from datetime import datetime as dt
from shutil import copy

from json import loads as jsonloads
from requests import get
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices

#pyinstaller --upx-dir  <your upx directory> --onefile --icon='icon.ico' --noconsole main.py

version = '1.0.1'
icon_path = 'icon.ico'

def check_and_create_folder(folder_path):
    if not exists(folder_path):
        makedirs(folder_path)
        print(f"폴더가 생성되었습니다: {folder_path}")
    else:
        print(f"폴더가 이미 존재합니다: {folder_path}")

check_and_create_folder('data')
check_and_create_folder('data/backup')


form_class = uic.loadUiType("breakcat.ui")[0]
encoding_per_index = {'shift_jis': 0, 'cp949' : 1, 'utf_8': 2, 'ascii': 3, 'gb2312': 4, 'big5': 5, 'mac_roman': 6, 'cp1252': 7}
encoding_name_to_friendly_alias = {'shift_jis': 'shift-jis', 'cp949' : 'cp949', 'utf_8': 'utf-8', 'ascii': 'ASCII', 'gb2312': 'GB2312', 'big5': 'Big5', 'mac_roman': 'macintosh', 'cp1252': 'windows-1252'}
cache_original ={'filename': '', 'oto': ''}
cache_converted = {'filename': '', 'oto': ''}

def convert_string(from_encoding: str, to_encoding: str, string: str) -> str:
    _ = string.encode(from_encoding)
    return _.decode(to_encoding, errors='ignore')

def fl_convert_string(from_encoding: str, to_encoding: str, _string: str) -> str:
    with open('data/$', 'w', encoding=from_encoding, errors='ignore') as f:
        f.write(_string)
        

    with open('data/$', 'r', encoding=from_encoding, errors='ignore') as f:
        string = f.read()

        
    cache_original['filename'] = string 
    _ = string.encode(from_encoding)
    return _.decode(to_encoding, errors='ignore')

try:
    if isfile('data/status'):
        '''{'visualFriend': 0(시각친화적 설정 on/off 여부), 'encodeFrom': 0(=콤보박스 1들의 인덱스번호, 0~8), 'decodeTo': 3(=콤보박스2들의 인덱스번호, 0~7), 'tabIndex': 메인 탭의 인덱스(0~1)}'''
        with open('data/status', 'rb') as f:
            encoding_status = pickle.load(f)
        if encoding_status['encodeFrom'] > 8:
            encoding_status['encodeFrom'] = 8    
    else:
        encoding_status = {'visualFriend': False, 'encodeFrom': 0, 'decodeTo': 0, 'tabIndex': 0, 'encodeFrom_oto': 0}
        with open('data/status', 'wb') as f:
            pickle.dump(encoding_status, f) 

except:
    encoding_status = {'visualFriend': False, 'encodeFrom': 0, 'decodeTo': 0, 'tabIndex': 0, 'encodeFrom_oto': 0}
    with open('data/status', 'wb') as f:
        pickle.dump(encoding_status, f)

    
#data initialization
main_status = {'disableSaveFilename': True, 'disableSaveOto': True,'disablePreviewFilename': True, 'disablePreviewOto': True, 'filenamePath': '', 'otoPath': '', 'fileNamePreview': [], 'otoPreview': [], 'fileNameTargets': [True, True, False, False, False], 'otherFileNamesList': [], 'encodings': ['shift-jis', 'cp949', 'utf-8', 'us-ascii', 'gb2312', 'big5', 'macintosh', 'windows-1252'], 'encodings_': ['shift-jis', 'cp949', 'utf-8', 'us-ascii', 'gb2312', 'big5', 'macintosh', 'windows-1252'],'detectedEncodingOto': '(auto)', 'detectedEncodingFilename': '(auto)'}
with open('data/cache', 'wb') as f:
    pickle.dump(main_status, f)
        

class FailedToReadOtoError(Exception):
    def __init__(self):
        super().__init__('Problem occured while loading your oto.')

class FailedToReadFilenameError(Exception):
    def __init__(self):
        super().__init__('Problem occured while loading your Filenames.')

class BreakCatWindow(QMainWindow, form_class):
    def __init__(self, app: QApplication):
        super().__init__()
        
        self.app = app
        self.kor_translator = QTranslator()
        self.kor_translator.load('lang/ko_KR.qm')
        _language_code =  self.readLang()
        self.setupUi(self)
        self._selectLanguage(_language_code)
        self.initUi()
        self.setFixedSize(832, 753)
        self.setWindowIcon(QIcon(icon_path))
        


    def _selectLanguage(self, code=int):
        '''About code:
        0 = ENG , 1 = KOR '''
        if code == 0:
            #English
            self.actionEnglish.setChecked(True)
            self.actionKorean.setChecked(False)
            self.setWindowTitle(f'BreakCat {version}')

            
        elif code == 1:
            #Korean
            self.actionEnglish.setChecked(False)
            self.actionKorean.setChecked(True)
            self.setWindowTitle(f'뷁캣 {version}')


    def readLang(self) -> int:
        if isfile('data/lang'):
            with open('data/lang', 'rb') as f:
                language_code = pickle.load(f)
            if language_code == 1:
                self.app.installTranslator(self.kor_translator)
                
            elif language_code == 0:
                pass
                
        else:
            language_code = 0
            with open('data/lang', 'wb') as f:
                pickle.dump(language_code, f)
        return language_code

    def initUi(self):
        with open('data/cache', 'rb') as f:
            main_status = pickle.load(f)
        
        self.actionEnglish.triggered.connect(self.changeLangToEnglish)
        self.actionKorean.triggered.connect(self.changeLangToKorean)
        self.actionUpdateCheck.triggered.connect(lambda: self.check_update(True))
        self.flButtonPreview.setDisabled(main_status['disablePreviewFilename'])
        self.otoButtonPreview.setDisabled(main_status['disablePreviewOto'])
        self.flButtonSave.setDisabled(main_status['disableSaveFilename'])
        self.otoButtonSave.setDisabled(main_status['disableSaveOto'])

        self.otoButtonFolderSelect.clicked.connect(self.loadOtoFile)
        self.flButtonFolderSelect.clicked.connect(self.loadFilenames)
        self.flButtonPreview.clicked.connect(self.convertFilenames)
        self.flButtonSave.clicked.connect(self.saveFilenames)
        self.otoButtonPreview.clicked.connect(self.convertOto)
        self.otoButtonSave.clicked.connect(self.saveOto)

        self.mainComboBox3.hide()
        self.mainComboBox4.hide()
        
        self.visualFriendlyMode.stateChanged.connect(self.setVisualFriendlyMode)
        self.visualFriendlyMode.setChecked(encoding_status['visualFriend'])
        
        if encoding_status['tabIndex'] == 0:
            self.mainComboBox1.currentIndexChanged.connect(partial(self.setComboBoxChanged, self.mainComboBox1, self.mainComboBox3, 'encodeFrom'))
            self.mainComboBox3.currentIndexChanged.connect(partial(self.setComboBoxChanged, self.mainComboBox3, self.mainComboBox1, 'encodeFrom'))
            self.mainComboBox2.currentIndexChanged.connect(partial(self.setComboBoxChanged, self.mainComboBox2, self.mainComboBox4, 'decodeTo'))
            self.mainComboBox4.currentIndexChanged.connect(partial(self.setComboBoxChanged, self.mainComboBox4, self.mainComboBox2, 'decodeTo'))
            
            self.mainComboBox1.setCurrentIndex(encoding_status['encodeFrom'])
            self.mainComboBox3.setCurrentIndex(encoding_status['encodeFrom'])
            self.mainComboBox2.setCurrentIndex(encoding_status['decodeTo'])
            self.mainComboBox4.setCurrentIndex(encoding_status['decodeTo'])
        
        else:
            self.mainComboBox1.currentIndexChanged.connect(partial(self.setComboBoxChanged, self.mainComboBox1, self.mainComboBox3, 'encodeFrom'))
            self.mainComboBox3.currentIndexChanged.connect(partial(self.setComboBoxChanged, self.mainComboBox3, self.mainComboBox1, 'encodeFrom'))
            self.mainComboBox2.currentIndexChanged.connect(partial(self.setComboBoxChanged, self.mainComboBox2, self.mainComboBox4, 'decodeTo'))
            self.mainComboBox4.currentIndexChanged.connect(partial(self.setComboBoxChanged, self.mainComboBox4, self.mainComboBox2, 'decodeTo'))

            self.mainComboBox1.setCurrentIndex(encoding_status['encodeFrom_oto'])
            self.mainComboBox3.setCurrentIndex(encoding_status['encodeFrom_oto'])
            self.mainComboBox2.setCurrentIndex(encoding_status['decodeTo'])
            self.mainComboBox4.setCurrentIndex(encoding_status['decodeTo'])
        
        
        self.tabWidget.currentChanged.connect(self.setTabChanged)
        self.tabWidget.setCurrentIndex(encoding_status['tabIndex'])
        self.mainComboBox2.setDisabled(main_status['disablePreviewOto'])
        self.mainComboBox4.setDisabled(main_status['disablePreviewOto'])

        if encoding_status['tabIndex'] == 1:
            self.mainComboBox1.setItemText(8, main_status['detectedEncodingOto'])
            self.mainComboBox3.setItemText(8, main_status['detectedEncodingOto'])

        otoOriginalViewModel = QStringListModel()
        otoOriginalViewModel.setStringList(cache_original['oto'].splitlines())
        otoPreviewModel = QStringListModel()
        otoPreviewModel.setStringList(cache_converted['oto'].splitlines())
        self.otoListviewOriginal.setModel(otoOriginalViewModel)
        self.otoListviewPreview.setModel(otoPreviewModel)

        flOriginalViewModel = QStringListModel()
        flOriginalViewModel.setStringList(cache_original['filename'].splitlines())
        flPreviewModel = QStringListModel()
        flPreviewModel.setStringList(cache_converted['filename'].splitlines())
        self.flListviewOriginal.setModel(flOriginalViewModel)
        self.flListviewPreview.setModel(flPreviewModel)

        self.otoTextReadonlyPath.setText(main_status['otoPath'])
        self.flTextReadonlyPath.setText(main_status['filenamePath'])

    def pickIndexFromEncoding(self, encoding_in_text: str) -> int:
        '''인코딩 명칭을 받아서 프로그램에서 사용하는 인덱스로 변환'''
        return encoding_per_index[encoding_in_text.lower()]
    
    def pickEncodingFromIndex(self, encoding_in_index: int) -> str:
        '''프로그램에서 사용하는 인덱스를 받아서 인코딩 명칭으로 변환'''
        return {val: key for key, val in encoding_per_index.items()}[encoding_in_index]

    def loadOtoFile(self):
        filepath, _ = QFileDialog.getOpenFileName(self, 'Open File',None, '(*.ini);;(*.txt)')
        if filepath != '':
            noError = True
            try:

                app.setOverrideCursor(QCursor(Qt.WaitCursor))
                with open(filepath, 'rb') as f:
                    encoding_detected = detect(f.read(1024))['encoding']

            
                try: 
                    main_status['detectedEncodingOto'] = f'auto:{encoding_name_to_friendly_alias[encoding_detected.lower()]}'
                
                except KeyError:
                    
                    main_status['detectedEncodingOto'] = f'auto:{encoding_detected}'
                except: 
                    app.restoreOverrideCursor()
                    noError = False
                    raise FailedToReadOtoError
                    
            
                if noError:
                    with open('data/cache', 'wb') as f:
                        pickle.dump(main_status, f)

                
                    with open('data/status', 'wb') as f:
                        pickle.dump(encoding_status, f)
                    
                    if len(main_status['encodings']) == 9:
                        main_status['encodings'][8] = encoding_detected
                    else:
                        main_status['encodings'].append(encoding_detected)
                    with open('data/cache', 'wb') as f:
                        pickle.dump(main_status, f)

                    with open(filepath, 'r', encoding=main_status['encodings'][encoding_status['encodeFrom_oto']], errors='ignore') as f:
                        cache_original['oto'] = f.read()
        

            except AttributeError:
                app.restoreOverrideCursor()
                msg_box = QMessageBox()
                msg_box.setWindowIcon(QIcon('icon.ico'))
                msg_box.setWindowTitle(f"(っ °Д °;)っ AttributeError")
                msg_box.setText(f"Your oto.ini is empty...")
                msg_box.addButton(" ✔️ Okay ", QMessageBox.RejectRole)

                msg_box.exec_()

            except Exception as e:
                app.restoreOverrideCursor()
                msg_box = QMessageBox()
                msg_box.setWindowIcon(QIcon('icon.ico'))
                msg_box.setWindowTitle(f"(っ °Д °;)っ {type(e).__name__}")
                msg_box.setText(f"{str(e)}")
                msg_box.addButton(" ✔️ Okay ", QMessageBox.RejectRole)

                msg_box.exec_()

            if noError:
                cache_converted['oto'] = ''

                self.mainComboBox1.setItemText(8, main_status['detectedEncodingOto'])
                self.mainComboBox3.setItemText(8, main_status['detectedEncodingOto'])
                
                
                main_status['otoPath'] = filepath
                
                self.otoTextReadonlyPath.setText(main_status['otoPath'])

                main_status['disablePreviewOto'] = False
                main_status['disableSaveOto'] = True

                self.otoButtonSave.setDisabled(main_status['disableSaveOto'])
                self.otoButtonPreview.setDisabled(main_status['disablePreviewOto'])
                
                
                self.mainComboBox2.setDisabled(main_status['disablePreviewOto'])
                self.mainComboBox4.setDisabled(main_status['disablePreviewOto'])


                otoPreviewModel = QStringListModel()
                otoPreviewModel.setStringList(cache_converted['oto'].splitlines())
                self.otoListviewPreview.setModel(otoPreviewModel)

                otoOriginalModel = QStringListModel()
                otoOriginalModel.setStringList([])
                self.otoListviewOriginal.setModel(otoOriginalModel)

            with open('data/cache', 'wb') as f:
                pickle.dump(main_status, f)

            app.restoreOverrideCursor()

#TODO 뒤로가기 버튼 구현
    # def keyPressEvent(self, event):
    #     if event.key() == Qt.Key_Z and event.modifiers() == Qt.ControlModifier:
    #         self.undo_delete()


    # def delete_item(self):
    #     selected_indexes = self.flListviewPreview.selectedIndexes()
    #     if selected_indexes:
    #         self.last_deleted_index = selected_indexes[0].row()
    #         self.model.removeRow(selected_indexes[0].row())

    # def undo_delete(self):
    #     if self.last_deleted_index is not None:
    #         self.model.insertRow(self.last_deleted_index)
    #         self.last_deleted_index = None


    def changeLangToEnglish(self):
        self.readLang()
        self._selectLanguage(0)
        language_code = 0
        with open('data/lang', 'wb') as f:
            pickle.dump(language_code, f)
        self.app.removeTranslator(self.kor_translator)
        self.setupUi(self)
        self.initUi()
        self._selectLanguage(0)
        
        
    def changeLangToKorean(self):
        self.readLang()
        self._selectLanguage(1)
        language_code = 1
        with open('data/lang', 'wb') as f:
            pickle.dump(language_code, f)
        self.app.installTranslator(self.kor_translator)
        self.setupUi(self)
    
        self.initUi()
        self._selectLanguage(1)

    def setVisualFriendlyMode(self):
        '''시각친화적 모드를 적용'''
        if self.visualFriendlyMode.isChecked():
            self.mainComboBox1.hide()
            self.mainComboBox3.show()
            self.mainComboBox4.show()
            self.mainComboBox2.hide()
            encoding_status['visualFriend'] = True
            with open('data/status', 'wb') as f:
                pickle.dump(encoding_status, f)
        else:
            self.mainComboBox1.show()
            self.mainComboBox3.hide()
            self.mainComboBox4.hide()
            self.mainComboBox2.show()
            encoding_status['visualFriend'] = False
            with open('data/status', 'wb') as f:
                pickle.dump(encoding_status, f)

    def setComboBoxChanged(self, _QcomboBox: QComboBox, fQcomboBox: QComboBox, key: str):
        '''key = encoding_status의 키 값
        QcomboBox의 인덱스가 움직이면 fQcomboBox의 인덱스도 함께 움직임'''
        main_status['disableSaveOto'] = True
        self.otoButtonSave.setDisabled(main_status['disableSaveOto'])
        main_status['disableSaveFilename'] = True
        self.flButtonSave.setDisabled(main_status['disableSaveFilename'])
        with open('data/cache', 'wb') as f:
            pickle.dump(main_status, f)
        if encoding_status['tabIndex'] == 0 and key == 'encodeFrom':
            index_changed = _QcomboBox.currentIndex()
            encoding_status['encodeFrom'] = index_changed
            fQcomboBox.setCurrentIndex( encoding_status['encodeFrom'])
        elif encoding_status['tabIndex'] == 1 and key == 'encodeFrom':
            index_changed = _QcomboBox.currentIndex()
            encoding_status['encodeFrom_oto'] = index_changed
            fQcomboBox.setCurrentIndex( encoding_status['encodeFrom_oto'])
        else:
            index_changed = _QcomboBox.currentIndex()
            encoding_status[key] = index_changed
            fQcomboBox.setCurrentIndex( encoding_status[key])

        with open('data/status', 'wb') as f:
            pickle.dump(encoding_status, f)
        
    def setTabChanged(self):
        index = self.tabWidget.currentIndex()
        encoding_status['tabIndex'] = index
        if index == 0:
            self.mainComboBox1.setCurrentIndex(encoding_status['encodeFrom'])
            self.mainComboBox3.setCurrentIndex(encoding_status['encodeFrom'])
            self.mainComboBox1.removeItem(8)
            self.mainComboBox3.removeItem(8)

        elif index == 1:
            self.mainComboBox1.removeItem(8)
            self.mainComboBox3.removeItem(8)
            
            self.mainComboBox1.addItem(main_status['detectedEncodingOto'])
            self.mainComboBox3.addItem(main_status['detectedEncodingOto'])
            self.mainComboBox1.setCurrentIndex(encoding_status['encodeFrom_oto'])
            self.mainComboBox3.setCurrentIndex(encoding_status['encodeFrom_oto'])

        with open('data/status', 'wb') as f:
            pickle.dump(encoding_status, f)

    def convertOto(self):
        app.setOverrideCursor(QCursor(Qt.WaitCursor))
        otopath = main_status['otoPath']
        try:
            main_status['disableSaveOto'] = True

            self.otoButtonSave.setDisabled(main_status['disableSaveOto'])
            with open(otopath, 'r', encoding=main_status['encodings'][encoding_status['encodeFrom_oto']], errors='ignore') as f:
                cache_original['oto'] = f.read()

                cache_converted['oto'] = convert_string(main_status['encodings'][encoding_status['encodeFrom_oto']], main_status['encodings'][encoding_status['decodeTo']], cache_original['oto'])

            otoOriginalViewModel = QStringListModel()
            otoOriginalViewModel.setStringList(cache_original['oto'].splitlines())

            otoPreviewModel = QStringListModel()
            otoPreviewModel.setStringList(cache_converted['oto'].splitlines())

            self.otoListviewOriginal.setModel(otoOriginalViewModel)
            self.otoListviewPreview.setModel(otoPreviewModel)

            main_status['disableSaveOto'] = False

            self.otoButtonSave.setDisabled(main_status['disableSaveOto'])

            with open('data/cache', 'wb') as f:
                pickle.dump(main_status, f)

        except Exception as e:
            msg_box = QMessageBox()
            msg_box.setWindowIcon(QIcon('icon.ico'))
            msg_box.setWindowTitle(f"(っ °Д °;)っ {type(e).__name__}")
            msg_box.setText(f"{str(e)}")
            msg_box.addButton(" ✔️ Okay ", QMessageBox.RejectRole)

            msg_box.exec_()

        app.restoreOverrideCursor()

    def saveOto(self):
        main_status['disableSaveOto'] = True
        self.otoButtonSave.setDisabled(main_status['disableSaveOto'])
        

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowIcon(QIcon('icon.ico'))
        msg_box.setWindowTitle(f"╰(￣ω￣ｏ) {main_status['encodings'][encoding_status['encodeFrom_oto']]} → {main_status['encodings'][encoding_status['decodeTo']]}")
        msg_box.setText(f"oto.ini를 저장할까요?\n결과는 되돌릴 수 없으니 신중히 결정해야 해요.")
        msg_box.addButton(" ✔️ Yes ", QMessageBox.AcceptRole)
        msg_box.addButton(" ❌ No ", QMessageBox.RejectRole)
        result = msg_box.exec_()
        try:
            if result == QMessageBox.AcceptRole:
            
                filesavepath, _ = QFileDialog.getSaveFileName(self, "Save oto.ini", main_status['otoPath'], "INI Files (*.ini);;All Files (*)")

                if filesavepath != '':
                    oto_backup_filepath = f"data/backup/{dt.now().strftime('%Y%m%d-%H%M%S')}_oto.ini"
                    with open(oto_backup_filepath, 'w') as f:
                        f.write('')

                    copy(main_status['otoPath'], oto_backup_filepath)

                    with open(filesavepath, 'w', encoding=main_status['encodings'][encoding_status['decodeTo']], errors='ignore') as save:
                        save.write(cache_converted['oto'])


                    msg_box = QMessageBox()
                    msg_box.setWindowIcon(QIcon('icon.ico'))
                    msg_box.setWindowTitle(f"(o゜▽゜)o☆ \^o^/ ")
                    msg_box.setText(f"oto.ini를 저장했어요.\n백업 파일은 [{oto_backup_filepath}]에 있답니다!")
                    msg_box.addButton(" ✔️ Okay ", QMessageBox.RejectRole)

                    msg_box.exec_()
            main_status['disableSaveOto'] = False
            self.otoButtonSave.setDisabled(main_status['disableSaveOto'])
        except Exception as e:
            app.restoreOverrideCursor()
            msg_box = QMessageBox()
            msg_box.setWindowIcon(QIcon('icon.ico'))
            msg_box.setWindowTitle(f"(っ °Д °;)っ {type(e).__name__}")
            msg_box.setText(f"{str(e)}")
            msg_box.addButton(" ✔️ Okay ", QMessageBox.RejectRole)

            msg_box.exec_()
            
            main_status['disableSaveOto'] = False
            self.otoButtonSave.setDisabled(main_status['disableSaveOto'])


    def loadFilenames(self):
        folderpath = QFileDialog.getExistingDirectory(None, "Select Voicebank Folder")
        if folderpath != '':
            app.setOverrideCursor(QCursor(Qt.WaitCursor))
            cache_original['_filename'] = f'\n'.join(listdir(folderpath))
            
            main_status['disablePreviewFilename'] = False
            
            try:

                with open('data/cache', 'wb') as f:
                    pickle.dump(main_status, f)

                
                with open('data/status', 'wb') as f:
                    pickle.dump(encoding_status, f)


            except AttributeError:
                app.restoreOverrideCursor()
                msg_box = QMessageBox()
                msg_box.setWindowIcon(QIcon('icon.ico'))
                msg_box.setWindowTitle(f"(っ °Д °;)っ AttributeError")
                msg_box.setText(f"Your Voicebank Folder is empty...")
                msg_box.addButton(" ✔️ Okay ", QMessageBox.RejectRole)

                msg_box.exec_()

            except Exception as e:
                app.restoreOverrideCursor()
                msg_box = QMessageBox()
                msg_box.setWindowIcon(QIcon('icon.ico'))
                msg_box.setWindowTitle(f"(っ °Д °;)っ {type(e).__name__}")
                msg_box.setText(f"{str(e)}")
                msg_box.addButton(" ✔️ Okay ", QMessageBox.RejectRole)

                msg_box.exec_()

            cache_converted['filename'] = ''

            main_status['filenamePath'] = folderpath
                
            self.flTextReadonlyPath.setText(main_status['filenamePath'])

            main_status['disablePreviewFilename'] = False
            main_status['disableSaveFilename'] = True

            self.flButtonSave.setDisabled(main_status['disableSaveFilename'])
            self.flButtonPreview.setDisabled(main_status['disablePreviewFilename'])
                
            self.mainComboBox2.setDisabled(main_status['disablePreviewFilename'])
            self.mainComboBox4.setDisabled(main_status['disablePreviewFilename'])


            flPreviewModel = QStringListModel()
            flPreviewModel.setStringList(cache_converted['filename'].splitlines())
            self.flListviewPreview.setModel(flPreviewModel)

            flOriginalModel = QStringListModel()
            flOriginalModel.setStringList([])
            self.flListviewOriginal.setModel(flOriginalModel)

            with open('data/cache', 'wb') as f:
                pickle.dump(main_status, f)

            app.restoreOverrideCursor()

    def convertFilenames(self):
        app.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:

            cache_converted['filename'] = fl_convert_string(main_status['encodings_'][encoding_status['encodeFrom']], main_status['encodings_'][encoding_status['decodeTo']], cache_original['_filename'])

            flOriginalViewModel = QStringListModel()
            flOriginalViewModel.setStringList(cache_original['filename'].splitlines())

            flPreviewModel = QStringListModel()
            flPreviewModel.setStringList(cache_converted['filename'].splitlines())

            self.flListviewOriginal.setModel(flOriginalViewModel)
            self.flListviewPreview.setModel(flPreviewModel)

            main_status['disableSaveFilename'] = False

            self.flButtonSave.setDisabled(main_status['disableSaveFilename'])

            with open('data/cache', 'wb') as f:
                pickle.dump(main_status, f)

        except Exception as e:
            msg_box = QMessageBox()
            msg_box.setWindowIcon(QIcon('icon.ico'))
            msg_box.setWindowTitle(f"(っ °Д °;)っ {type(e).__name__}")
            msg_box.setText(f"{str(e)}")
            msg_box.addButton(" ✔️ Okay ", QMessageBox.RejectRole)

            msg_box.exec_()

        app.restoreOverrideCursor()

    def saveFilenames(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowIcon(QIcon('icon.ico'))
        msg_box.setWindowTitle(f"╰(￣ω￣ｏ) {main_status['encodings'][encoding_status['encodeFrom']]} → {main_status['encodings'][encoding_status['decodeTo']]}")
        msg_box.setText(f"파일명을 변환할까요?\n결과는 되돌릴 수 없으니 신중히 결정해야 해요.")
        msg_box.addButton(" ✔️ Yes ", QMessageBox.AcceptRole)
        msg_box.addButton(" ❌ No ", QMessageBox.RejectRole)

        result = msg_box.exec_()
        if result == QMessageBox.AcceptRole:
            try:
                for filename, new_filename in zip(cache_original['_filename'].splitlines(), cache_converted['filename'].splitlines()):
                # 파일이 존재하는지 확인합니다.
                    file_path = join_(main_status['filenamePath'], filename)
                    if not isfile(file_path):
                        print(f"No file: {file_path}")
                        return

                    # 파일의 디렉토리 경로와 기존 파일명을 추출합니다.
                    directory, old_filename = split_(file_path)
    
                    # 새로운 파일명으로 변경합니다.
                    new_file_path = join_(directory, new_filename)
                    rename(file_path, new_file_path)
                    print(f"Changed Filename: {old_filename} -> {new_filename}")

                msg_box = QMessageBox()
                msg_box.setWindowIcon(QIcon('icon.ico'))
                msg_box.setWindowTitle(f"o(*￣︶￣*)o")
                msg_box.setText(f"파일명 변환을 완료했어요")
                msg_box.addButton("✔️ Okay ", QMessageBox.RejectRole)

                msg_box.exec_()
            except Exception as e:
                msg_box = QMessageBox()
                msg_box.setWindowIcon(QIcon('icon.ico'))
                msg_box.setWindowTitle(f"(っ °Д °;)っ {type(e).__name__}")
                msg_box.setText(f"{str(e)}")
                msg_box.addButton(" ✔️ Okay ", QMessageBox.RejectRole)

                msg_box.exec_()

    def check_update(self, version_check: bool):
        owner = "EX3exp"
        repo = "BreakCat"

        api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        response = get(api_url)

        if response.status_code == 200:
            response_text = response.text
            release_info = jsonloads(response_text)

            latest_version = release_info["tag_name"]

            if latest_version != version:
                download_link = f"https://github.com/EX3exp/BreakCat/releases/download/{latest_version}/BreakCat{latest_version}.zip"
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Information)
                msg_box.setWindowIcon(QIcon('icon.ico'))
                msg_box.setWindowTitle(f"Update v{version} → v{latest_version}")
                msg_box.setText(f"🤔뷁캣이 v{latest_version}으로 업데이트되었어요!")
                msg_box.setInformativeText("바로 다운로드 링크로 이동할까요?")
                msg_box.addButton(" ✔️ Download Now ", QMessageBox.AcceptRole)
                msg_box.addButton(" ❌ No ", QMessageBox.RejectRole)

                result = msg_box.exec_()

                if result == QMessageBox.AcceptRole:
                    QDesktopServices.openUrl(QUrl(download_link))

            elif version_check:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Information)
                msg_box.setWindowIcon(QIcon('icon.ico'))
                msg_box.setWindowTitle(f"v{version}")
                msg_box.setText(f"😎뷁캣이 현재 최신 버전이에요.")
                msg_box.addButton(" ✔️ Okay ", QMessageBox.RejectRole)

                result = msg_box.exec_()
            else:
                pass
        elif version_check:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowIcon(QIcon('icon.ico'))
            msg_box.setWindowTitle(f"v{version} - UpdateCheckError")
            msg_box.setText(f"🫠오, 이런. 오류가 발생해 업데이트 체킹에 실패했어요.")
            msg_box.addButton(" 🫠 Okay ", QMessageBox.RejectRole)

            result = msg_box.exec_()
        else:
            pass
if __name__ == "__main__":
    def delCache():
        try:
            remove('data/cache')
            remove('data/$')
        except:
            pass

    app = QApplication(sys.argv)
    app.aboutToQuit.connect(delCache)
    breakCatWindow = BreakCatWindow(app)
    
    breakCatWindow.show()
    breakCatWindow.check_update(False)

    sys.exit(app.exec_())
    
    
