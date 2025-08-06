# -*- coding: utf-8 -*-

from PIL import Image, ImageOps, ImageFilter
import numpy as np
import matplotlib.pyplot as plt
import zlib
import io
from base64 import b64encode as b64e
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.concatkdf import ConcatKDFHMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding



MAXSIZE = 512
MAXVAL = 0x7fffffff


def iconize(fname, size=64):
    img = Image.open(fname).convert('RGBA')
    img = ImageOps.pad(img, (size,size), color='#00000000')
    return img


def imageto64(img):
    b = io.BytesIO()
    img.save(b, format="PNG")
    img64 = b64e(b.getvalue())
    return img64


def square_img(img):
    img = img.convert("RGBA")
    img = ImageOps.pad(img, (MAXSIZE,MAXSIZE), color='#00000000')
    return img


def preprocess_img(fname, maxsize):
    img = Image.open(fname).convert('RGBA')
    img = img.resize((maxsize*img.width//img.height,maxsize) if img.height > img.width else (maxsize,maxsize*img.height//img.width))
    img = img.convert("RGBA").filter(ImageFilter.SMOOTH).filter(ImageFilter.SHARPEN).filter(ImageFilter.SMOOTH).filter(ImageFilter.SHARPEN).quantize(255)
    return img


def RGBA_img(img):
    img = img.resize((MAXSIZE*img.width//img.height,MAXSIZE) if img.height > img.width else (MAXSIZE,MAXSIZE*img.height//img.width))
    return img.convert("RGBA").quantize(255)


def img_empty(size):
    img = Image.new("RGBA", (size, size), "#ffffff00")
    return imageto64(img)


def init_crypt(passwd,salt):
    ckdf = ConcatKDFHMAC(
        algorithm=hashes.SHA256(),
        length=16,
        salt=salt,
        otherinfo=b"initial vector",
    )
    iv = ckdf.derive(passwd)
    
    ckdf = ConcatKDFHMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        otherinfo=b"AESkey",
    )
    key = ckdf.derive(passwd)
    return Cipher(algorithms.AES(key), modes.CBC(iv))
        

def get_psrng(passwd,salt):
    ckdf = ConcatKDFHMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        otherinfo=b"pseudorandom-seed",
    )
    seed = np.frombuffer(ckdf.derive(passwd),dtype=np.uint)
    return np.random.Generator(np.random.MT19937(seed))
    

def get_plot(n, values, color):
    fig = plt.figure()
    if n > 0:
        plt.bar(np.arange(n),np.repeat(values,2),color=color)
    fig.suptitle('Distances between pairs of colors', fontsize=20)
    plt.xlabel('Colors', fontsize=16)
    plt.ylabel('Distance', fontsize=16)
    bin_stream = io.BytesIO()
    plt.savefig(bin_stream)
    plt.close(fig)
    return b64e(bin_stream.getvalue())
  
  
def get_capabilities(img, max_error):
    
    h = img.histogram()
    num_colors = int(np.count_nonzero(h))                                       
    pal = np.zeros((256,4),np.uint8)                                      
    pal[:len(img.palette.palette)//4] = np.frombuffer(img.palette.palette,np.uint8).reshape(-1,4)      
    distances = np.full((num_colors,num_colors),MAXVAL,dtype=np.uint)                           
       
    for i in range(1,num_colors):
        distances[i,0:i] = np.sum((pal[np.arange(0,i)].astype(int)-pal[i].astype(int))**2,axis=1)
    
    values = []
    capacity = 0
    maxd = 0
    colors_used = []    
    
    while True:
        mind = np.amin(distances)
        if(mind <= max_error):
            maxd = mind
            values.append(mind)
            pair = np.unravel_index(np.argmin(distances), distances.shape)
            colors_used.append(pair[0])
            colors_used.append(pair[1])
            distances[pair[0],:] = MAXVAL
            distances[pair[1],:] = MAXVAL
            distances[:,pair[0]] = MAXVAL
            distances[:,pair[1]] = MAXVAL
            capacity += (h[pair[0]]+h[pair[1]])       
        else:
            break
    
    if len(colors_used) == 0:
        color = None
    else:
        color = (pal[np.array(colors_used).flatten()]/255).tolist()
        
    info = "Total number of colors in image: %d\nPairs of colors used: %d\nResulting capacity (bytes): %d\nMaximum distance between colors in pairs: %d (next %d)" % (num_colors, len(colors_used), capacity//8, maxd, mind)
    return (get_plot(len(colors_used), values, color), info)


def encrypt(img, password, msg, max_error, output_name):

    rng = np.random.default_rng()   
    salt = rng.bytes(2)
    
    bin_msg = zlib.compress(msg.encode())
    padder = padding.PKCS7(128).padder()
    bin_msg = padder.update(bin_msg) + padder.finalize()
    encryptor = init_crypt(password,salt).encryptor()
    bin_msg = encryptor.update(bin_msg) + encryptor.finalize()
    msg_len = len(bin_msg)
    payload = msg_len*8+16
      
    h = img.histogram()
    num_colors = int(np.count_nonzero(h)) 
    pal = np.zeros((256,4),np.uint8)                                      
    pal[:len(img.palette.palette)//4] = np.frombuffer(img.palette.palette,np.uint8).reshape(-1,4)      
    distances = np.full((num_colors,num_colors),MAXVAL,dtype=np.uint) 
    vals = np.array(img.getchannel(0))
    
    for i in range(1,num_colors):
        distances[i,0:i] = np.sum((pal[np.arange(0,i)].astype(int)-pal[i].astype(int))**2,axis=1)
    
    pairs = []
    values = []
    capacity = 0
    odds = []
    evens = []       
    while capacity <= payload:
        mind = np.amin(distances)
        if(mind <= max_error):
            maxd = mind
            values.append(mind)
            pair = np.unravel_index(np.argmin(distances), distances.shape)
            pairs.append(pair)
            odds.append(pair[0])
            evens.append(pair[1])
            distances[pair[0],:] = MAXVAL
            distances[pair[1],:] = MAXVAL
            distances[:,pair[0]] = MAXVAL
            distances[:,pair[1]] = MAXVAL
            capacity += (h[pair[0]]+h[pair[1]])       
        else:
            return [1, None, None]
            
    npairs = len(pairs)
    used = np.concatenate((odds,evens))
    
    chart = get_plot(used.shape[0], values, (pal[np.array(pairs).flatten()]/255).tolist())
    info = "Total number of colors in image: %d\nPairs of colors used: %d\nResulting capacity (bytes): %d\nResulting payload (bytes): %d\nMaximum distance between colors in pairs: %d" % (num_colors, npairs, capacity//8, payload//8,maxd)
    
    newp = np.zeros((256,4),np.uint8)
    rng.shuffle(odds)
    rng.shuffle(evens)
    ntbl = np.full(256,255,dtype=np.uint8)
    
    for i in range(npairs):
        newp[2*i] = pal[evens[i]]
        newp[2*i+1] = pal[odds[i]]
        ntbl[evens[i]] = 2*i
        ntbl[odds[i]] = 2*i+1
        
    left = np.delete(np.arange(num_colors),used) 
    rng.shuffle(left)
      
    for i in range(len(left)):
        newp[2*npairs+i] = pal[left[i]]
        ntbl[left[i]] = 2*npairs+i
        
    s = np.frombuffer(salt,dtype=np.uint8)
    newp[2*npairs+1+i,0] = np.bitwise_xor.reduce(s)^(2*npairs) 
    newp[2*npairs+1+i,1:3] = s
    
    for i in range(2*npairs+2+i,256):
        newp[i] = newp[i-1]
    
    chgtbl = np.array(range(256))
    for pair in pairs:
        chgtbl[ntbl[pair[0]]] = ntbl[pair[1]]
        chgtbl[ntbl[pair[1]]] = ntbl[pair[0]]
        
    newv = ntbl[vals].flatten()
    
    ## ENCODER
    data = np.unpackbits(np.frombuffer(msg_len.to_bytes(2,'big')+bin_msg,np.uint8))
    psrng = get_psrng(password, salt)
    points = psrng.choice(np.argwhere(newv < 2*npairs),capacity,False)[:len(data)]
    changed = points[(data != (newv[points]%2).flatten())]
    np.put(newv,changed,chgtbl[newv[changed]]) 
    
    imge = Image.fromarray(newv.reshape((img.height,img.width)),mode='P')
    imge.putpalette(newp.reshape(1024).tolist(),rawmode="RGBA")
    imge.save(output_name,format="PNG")
    
    return [0, imge, (chart, info)]
    

def decrypt(password, src):

    img = Image.open(src)
    
    if img.mode != 'P':
        return [2, None]
    
    vals = np.array(img.getchannel(0)).flatten()
    pal = np.zeros((256,3),np.uint8)                                      
    pal[:len(img.palette.palette)//3] = np.frombuffer(img.palette.palette,np.uint8).reshape(-1,3)
    salt = pal[255][1:].tobytes()
    num_used_colors = np.bitwise_xor.reduce(pal[255])
    mask = np.argwhere(vals < num_used_colors)
    capacity = len(mask)
    
    psrng = get_psrng(password, salt)
    points = psrng.choice(mask,capacity,False)
    if len(points) < 18:
        return [2, None]
    data = (vals[points]%2).flatten()
    
    try:
        msglen = int.from_bytes(np.packbits(data[:16]).tobytes(),'big')
        msgb = np.packbits(data[16:msglen*8+16]).tobytes()
        decryptor = init_crypt(password,salt).decryptor()
        msgb = decryptor.update(msgb) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        msgb = unpadder.update(msgb) +  unpadder.finalize()
        msg = zlib.decompress(msgb).decode()
    except:
        return [1, None]
    return [0,msg]
