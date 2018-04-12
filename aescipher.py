from Crypto.Cipher import AES

BS = AES.block_size
pad =lambda s: s +(BS - len(s)% BS)* chr(BS - len(s)% BS)
unpad =lambda s : s[0:-ord(s[-1])]

def decrypt(sourcefile, targetfile):
    print('pleae input the decipher key:')
    key = input()
    g = open(sourcefile, 'rb')
    cipher = AES.new(key)
    encrypted = g.read()
    text = unpad(cipher.decrypt(encrypted).decode('utf-8'))
    g.close()

    f = open(targetfile, 'w')
    f.write(text)
    f.close()


def encrypt(sourcefile, targetfile):
    print('pleae input the encipher key:')
    key = input()
    h= open(sourcefile, 'r')
    text = h.read()
    h.close()
    cipher = AES.new(key)

    encrypted = cipher.encrypt(pad(text))
    i=open(targetfile,'wb')
    i.write(encrypted)
    i.close()

#encrypt("test122.json","config122.json")
decrypt("config122.json","test1122.json")
