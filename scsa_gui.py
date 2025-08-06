# -*- coding: utf-8 -*-

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import scsa
import PySimpleGUI as sg
import os.path
import imghdr
import time



def check_enable_encrypt():
    disabled = not(encrypt_image != None and '' not in [window['encrypt-password'].get(), window['encrypt-multiline'].get(), window['encrypt-output-file'].get()])
    window['encrypt-encrypt'].update(disabled=disabled)


def check_enable_start():
    disabled = not(not started and '' not in [window['decrypt-input-dir'].get(), window['decrypt-auto-password'].get()])
    window['decrypt-start'].update(disabled=disabled)
     
    
def check_enable_try():
    disabled = not(window['decrypt-user-password'].get() != '' and decrypt_image != None)
    window['decrypt-try-again'].update(disabled=disabled)


def create_tree(rootf):
    tree_data = sg.TreeData()
    if not os.path.isdir(rootf):
        window['decrypt-tree'].update(values=tree_data)
        return
    tree_data.insert('', os.path.abspath(rootf), os.path.split(rootf)[1], values=[])
    for root, dirs, files in os.walk(rootf):
        root = os.path.abspath(root)
        for name in dirs:
            tree_data.insert(root, os.path.join(root, name), name, values=[])
        for name in files:
            file = os.path.join(root, name)
            if imghdr.what(file) == 'png':
                file_icon = scsa.imageto64(scsa.iconize(file,32))
                tree_data.insert(root, file, ' '+name, values=[], icon=file_icon)
    window['decrypt-tree'].update(values=tree_data)


def show_decrypted(password, img_path, isUser=True):
    error,msg = scsa.decrypt(password.encode(), img_path)
    image_name = os.path.split(img_path)[1]
    window['decrypt-multiline'].print('\n' + '-'*50, text_color='#000000')
    if error == 0:
        color = '#66ff66'
    else:
        color = '#ff6666'
        
    if isUser:
        window['decrypt-multiline'].print('\nDecrypting message inside ', image_name, '...', text_color=color)
    else:
        window['decrypt-multiline'].print('\nNew image recieved! Name:', os.path.split(img_path)[1], text_color=color)
        window['decrypt-multiline'].print('\nDecrypting message...', text_color=color)
    if error == 0:
        window['decrypt-multiline'].print('\nMessage decrypted:\n', text_color=color)
        window['decrypt-multiline'].print(msg)
    if error == 1:
        window['decrypt-multiline'].print('ERROR - WRONG PASSWORD OR BAD ENCODED', text_color=color)
    elif error == 2:
        window['decrypt-multiline'].print('Incompatible image', text_color=color)
    window['decrypt-last-image'].update(data=scsa.imageto64(scsa.iconize(img_path,MAXSIZE)))


def reset_encrypt_tab():
    window['encrypt-input-dir'].update('')
    window['encrypt-image-chosen'].update(data=scsa.img_empty(MAXSIZE))
    window['encrypt-encrypt'].update(disabled=True)
    window['encrypt-show-capabilities'].update(disabled=True)
    window['encrypt-show-details'].update(disabled=True)
    window['encrypt-multiline'].update('')
    window['encrypt-chars-fill'].update('')
    window['encrypt-image-name'].update('')
    window['encrypt-password'].update('')
    window['encrypt-output-file'].update('')
    empty_images()


def reset_decrypt_tab():
    window['decrypt-input-dir'].update('')
    window['decrypt-auto-password'].update('', disabled=False)
    window['decrypt-user-password'].update('', disabled=False)
    window['decrypt-try-again'].update(disabled=True)
    window['decrypt-start'].update(disabled=True)
    window['decrypt-multiline'].update('')
    window['decrypt-tree'].update(values=sg.TreeData())
    window['decrypt-last-image'].update(data=scsa.img_empty(MAXSIZE))

    
def empty_images():
    for i in range(len(active_button_image)):
        window[active_button_image[i]].update(image_data=scsa.img_empty(64), disabled=True)


def fill_images():
    empty_images()
    folder = values['encrypt-input-dir']
    try:
        file_list = os.listdir(folder)
    except:
        file_list = []

    fnames = [
        os.path.join(folder, f)
        for f in file_list
        if os.path.isfile(os.path.join(folder, f))
            and imghdr.what(os.path.join(folder, f)) != None
    ]
    for i in range(min(len(fnames),90)):
        button = 'button_image%d' % (i)
        window[button].update(image_data=scsa.imageto64(scsa.iconize(fnames[i])), disabled=False)
        window[button].metadata=fnames[i]
        active_button_image.append(button)


def recieved_file(event):
    global prev_event
    global decrypt_image
    
    time.sleep(0.1)
    path = event.src_path
    if (prev_event is None or event != prev_event) and os.path.isfile(path):
        prev_event = event
        
        if imghdr.what(path) == 'png':
            decrypt_image = path
            show_decrypted(window['decrypt-auto-password'].get(), decrypt_image, False)
            check_enable_try()
            create_tree(window['decrypt-input-dir'].get())



FILECHARS='ramdom_text.txt'
MAXSIZE=512

if __name__ == '__main__':
    patterns = None
    ignore_patterns = None
    ignore_directories = True
    case_sensitive = False
    my_event_handler = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)
    prev_event = None
    
    
sg.theme('DarkTeal9')
sg.set_options(font=('Courier New', 10))


encrypt_layout = [
                    
                    [
                        sg.Text('Image Folder'),
                        sg.In(size=(15, 1), enable_events=True, key='encrypt-input-dir'),
                        sg.FolderBrowse(),
                        sg.Text('', size=(20, 1)),
                        sg.Text('', key='encrypt-image-name', font=('Courier New', 14))
                    ],
                    [
                        sg.Column([
                
                            [sg.Button('', key='button_image%d' % (3*j+i), visible=True, image_data=scsa.img_empty(64), disabled=True) for i in range(3)] for j in range(30)
                                
                        ],scrollable=True, vertical_scroll_only=True, visible=True, key='encrypt-images-column', vertical_alignment='c',s=(None,530)),
                        
                        sg.Column([
                            
                            [sg.Image(key='encrypt-image-chosen', data=scsa.img_empty(MAXSIZE))],
                            [
                                sg.Button('Capabilities', key='encrypt-show-capabilities', disabled=True), 
                                sg.Button('Details', key='encrypt-show-details', disabled=True),
                                sg.Text('Max distance', size=(13, 1)),
                                sg.Spin([i for i in range(1,10000)], initial_value=100, size=(5,1), key='encrypt-max-distance')
                            ]
                            
                        ], element_justification='c'),
                        
                        sg.Column([
                            
                            [
                                sg.Text('Password', size=(14, 1)), 
                                sg.InputText(key='encrypt-password',size=(20,1), enable_events=True),
                                sg.Text(' ', size=(9, 1))
                            ],
                            [
                                sg.Text('Output image', size=(14, 1)),
                                sg.In(size=(20, 1), enable_events=True, key='encrypt-output-file'),
                                sg.FileSaveAs(font=('Courier New', 8), size=(10,1))
                            ],
                            [sg.Multiline(size=(50, 25), key='encrypt-multiline', enable_events=True)],
                            [
                                sg.Button('Clear', size=(10,1), key='encrypt-clear-multiline'), sg.Text('Chars to fill'), 
                                sg.InputText(key='encrypt-chars-fill',size=(10,1), tooltip='Introduce number of characters to fill the text message.'), 
                                sg.Button('Fill', size=(10,1), key='encrypt-fill-multiline')
                            ],
                            [sg.Text(' ')],
                            [
                                sg.Button('Encrypt', size=(15,1), key='encrypt-encrypt', disabled=True), 
                                sg.Button('Reset', size=(15,1), key='encrypt-reset')
                            ]
                            
                        ], vertical_alignment='t', element_justification='c')
                    ]
                ]

decrypt_layout = [  
            
                    [
                        sg.Text('Root Folder'),
                        sg.In(size=(15, 1), enable_events=True, key='decrypt-input-dir'),
                        sg.FolderBrowse()
                    ],
                    [
                        sg.Column([
                            
                            [sg.Tree(data=sg.TreeData(),
                             headings=[],
                             auto_size_columns=True,
                             row_height=34,
                             select_mode=sg.TABLE_SELECT_MODE_EXTENDED,
                             num_rows=15,
                             col0_width=27,
                             key='decrypt-tree',
                             show_expanded=True,
                             enable_events=True)]
                                    
                        ],vertical_alignment='c', s=(245,530)),
                        
                        sg.Column([
                            
                            [sg.Image(key='decrypt-last-image',data=scsa.img_empty(MAXSIZE))]
                            
                        ],vertical_alignment='t', element_justification='c'),
                        
                        sg.Column([
                            
                            [
                                sg.Text('Auto-Password', size=(14, 1)), 
                                sg.InputText(key='decrypt-auto-password',size=(20,1), enable_events=True),
                                sg.Text(' ', size=(9, 1))
                            ],
                            [
                                sg.Text('User-password', size=(14, 1)),
                                sg.InputText(size=(20, 1), enable_events=True, key='decrypt-user-password'),
                                sg.Button('Try again', size=(10,1), key='decrypt-try-again', font=('Courier New', 8), disabled=True)
                            ],
                            [sg.Multiline(size=(50, 25), key='decrypt-multiline', enable_events=True)],
                            [
                                sg.Button('Clear console', size=(20,1), key='decrypt-clear-multiline')
                            ],
                            [sg.Text(' ')],
                            [
                                sg.Button('Start', size=(15,1), key='decrypt-start', disabled=True,), 
                                sg.Button('Reset', size=(15,1), key='decrypt-reset')
                            ]
                            
                        ], vertical_alignment='t', element_justification='c')   
                    ]
                ]

layout = [[sg.TabGroup([[sg.Tab('Encryptor tool', encrypt_layout), sg.Tab('Decryptor tool', decrypt_layout)]])]]
window = sg.Window('SIMILAR COLOR SWAPPING APPLICATION (SCSA)', layout, element_justification='c').finalize()


my_event_handler.on_created = recieved_file
my_observer = Observer()
my_observer.start()


encrypt_image = None
decrypt_image = None
active_button_image = []
info = None
started = False

while True:
    event, values = window.read()
    
    if event in ['encrypt-password', 'encrypt-multiline', 'encrypt-output-file']:
        check_enable_encrypt()
    
    if event == None:
        if my_observer.is_alive():
            my_observer.stop()
            my_observer.join()
        break

#ENCRYPT EVENTS

    elif event == 'encrypt-input-dir':
        fill_images()
        
    elif event[:len('button_image')] == 'button_image':
        file = window[event].metadata
        if(os.path.isfile(file)):
            encrypt_image = scsa.preprocess_img(file, MAXSIZE)  
            window['encrypt-image-chosen'].update(data=scsa.imageto64(scsa.square_img(encrypt_image)))
            window['encrypt-image-name'].update(os.path.split(file)[1])
            window['encrypt-show-details'].update(disabled=True)
            window['encrypt-show-capabilities'].update(disabled=False)
            check_enable_encrypt()
        else:
            sg.PopupOK('Had a problem opening that file. It appears to be inexistent. Refreshing image folder...', non_blocking=True, title='ERROR')
            fill_images()
            
    elif event == 'encrypt-show-capabilities':
        max_error = values['encrypt-max-distance'] if values['encrypt-max-distance'] in range(1,10000) else 100
        window['encrypt-max-distance'].update(value=max_error)
        img_info = scsa.get_capabilities(encrypt_image, max_error)
        sg.PopupNoButtons(img_info[1], title='IMAGE ENCRYPTION CAPABILITIES', image=img_info[0])
        
    elif event == 'encrypt-fill-multiline':
        try:
            numchars = int(values['encrypt-chars-fill'])
            with open(FILECHARS, 'r') as f:
                data = f.read(numchars)
            window['encrypt-multiline'].update(data)
            window['encrypt-chars-fill'].update('')
            check_enable_encrypt()
        except:
            pass
        
    elif event == 'encrypt-clear-multiline':
        window['encrypt-multiline'].update('')
        window['encrypt-chars-fill'].update('')
        
    elif event == 'encrypt-encrypt':
        pass_encrypt = values['encrypt-password'].encode()
        msg_encrypt = values['encrypt-multiline']
        dest_file = values['encrypt-output-file']
        max_error = values['encrypt-max-distance'] if values['encrypt-max-distance'] in range(1,10000) else 100
        window['encrypt-max-distance'].update(value=max_error)
        if encrypt_image != None and '' not in [pass_encrypt, msg_encrypt, dest_file]:
            error, sent_image, info = scsa.encrypt(encrypt_image, pass_encrypt, msg_encrypt, max_error, dest_file)
            if error == 0:
                encrypt_image = scsa.RGBA_img(sent_image)
                sg.PopupAutoClose('Encryption succesful! You can check now encryption details.', non_blocking=True, title='INFO', auto_close_duration=2)
                window['encrypt-image-chosen'].update(data=scsa.imageto64(scsa.square_img(sent_image)))
                window['encrypt-image-name'].update(os.path.split(dest_file)[1])
                window['encrypt-show-details'].update(disabled=False)
            else:
                sg.PopupOK('Not enough capacity in the image. Try increasing the max distance or picking other image.', title='ERROR')
        else:
            sg.PopupOK('AN EXCEPTION OCCURRED! Reseting...', title='ERROR', non_blocking=True)
            reset_encrypt_tab()
            
    elif event == 'encrypt-show-details':
        sg.PopupNoButtons(info[1], title='ENCRYPTION DETAILS', image=info[0])
        
    elif event == 'encrypt-reset':
        encrypt_image = None
        reset_encrypt_tab()
    
#DECRYPT EVENTS    
    
    elif event == 'decrypt-input-dir':
        create_tree(window['decrypt-input-dir'].get())
        check_enable_start()
    
    elif event == 'decrypt-tree':
        selected = values['decrypt-tree'][0]
        password_decrypt = window['decrypt-user-password'].get()
        if password_decrypt == '':
            password_decrypt = window['decrypt-auto-password'].get()
        if os.path.exists(selected):
            if os.path.isfile(selected) and imghdr.what(selected) == 'png':
                if password_decrypt != '':
                    decrypt_image = selected
                    show_decrypted(password_decrypt, decrypt_image)
                    check_enable_try()
                else:
                    sg.PopupOK('You must give a user password to decrypt.', title='INFO')
        else:
            sg.PopupOK('Had a problem opening that file/dir. It appears to be inexistent. Refreshing root folder...', non_blocking=True, title='ERROR')
            create_tree(values['decrypt-input-dir'])
    
    elif event == 'decrypt-auto-password':
        check_enable_start()
        
    elif event == 'decrypt-user-password':
        check_enable_try()
        
    elif event == 'decrypt-try-again':
        show_decrypted(window['decrypt-user-password'].get(), decrypt_image)
    
    elif event == 'decrypt-start':
        folder = values['decrypt-input-dir']
        if os.path.isdir(folder):
            my_observer.schedule(my_event_handler, values['decrypt-input-dir'], recursive=True)
            started = True
            window['decrypt-auto-password'].update(disabled=True)
            window['decrypt-start'].update(disabled=True)
        else:
            sg.PopupOK('Bad root folder. Check it and try again!', title='ERROR')
            started = False
                       
    elif event == 'decrypt-clear-multiline':
        window['decrypt-multiline'].update('')

    elif event == 'decrypt-reset':
        if started:
            my_observer.unschedule_all()
            started = False
        reset_decrypt_tab()
        
window.close()
