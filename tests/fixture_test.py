#!/usr/bin/env python3
"""Deterministic synthetic PGS, VobSub and HD-DVD fixture tests for the native CLI."""
import pathlib, struct, subprocess, sys, tempfile, xml.etree.ElementTree as ET

cli = sys.argv[1]
be16=lambda x: struct.pack('>H',x)
be32=lambda x: struct.pack('>I',x)

def run(*args):
    p=subprocess.run([cli,*(str(a) for a in args)],capture_output=True,text=True)
    if p.returncode: raise AssertionError(f'command {args}: {p.returncode} {p.stderr}')

def pg(t,typ,data): return b'PG'+be32(t)+be32(t)+bytes([typ])+be16(len(data))+data

def check_xml(path):
    root=ET.parse(path).getroot()
    e=root.find('.//Event')
    assert e is not None and int(e.find('Graphic').attrib['Width'])>=1
    image=path.parent/e.find('Graphic').text
    assert image.is_file() and image.read_bytes()[:8]==b'\x89PNG\r\n\x1a\n'
    return e

with tempfile.TemporaryDirectory() as d:
    d=pathlib.Path(d)
    # One 2 x 2 PGS object, RLE run of two white pixels per scanline;
    # true transparent index 0, real palette entry index 1.
    pds=bytes([0,0,0,16,128,128,0,1,210,128,128,255])
    pcs=be16(1920)+be16(1080)+bytes([0x10])+be16(1)+bytes([0x80,0,0,1])+be16(0)+bytes([0,0x40])+be16(100)+be16(200)
    clear=be16(1920)+be16(1080)+bytes([0x10])+be16(2)+bytes([0,0,0,0])
    ods=be16(0)+bytes([0,0xc0])+bytes([0,0,12])+be16(2)+be16(2)+bytes([0,0x82,1,0,0,0x82,1,0,0])
    data=pg(90000,0x16,pcs)+pg(90000,0x14,pds)+pg(90000,0x15,ods)+pg(90000,0x80,b'')+pg(180000,0x16,clear)+pg(180000,0x80,b'')
    (d/'in.sup').write_bytes(data)
    run(d/'in.sup',d/'pal.xml','/res:pal','/fps:25','/tmin:0','/tmerge:0','/forced-')
    e=check_xml(d/'pal.xml');assert e.attrib['Forced']=='True' and e.find('Graphic').attrib['Y']=='107'
    run(d/'in.sup',d/'second.sup','/res:720p')
    assert (d/'second.sup').read_bytes().startswith(b'PG')
    run(d/'second.sup',d/'roundtrip.xml','/res:1080p')
    check_xml(d/'roundtrip.xml')
    # Native DVD VobSub with two 2px interlaced lines, sequential DCSQs.
    base=bytearray([0,0,0,6,0x90,0x90]); seq=bytearray()
    seq+=be16(0)+be16(30)+bytes([1,3,0x01,0x23,4,0xFF,0xFF,5,0,0,1,0,0,1,6,0,4,0,5,255])
    assert len(seq)==24
    seq+=be16(90)+be16(30)+bytes([2,255]);base+=seq;base[0:2]=be16(len(base))
    assert len(base)==36
    # VobSub packet: MPEG2 PES private_stream_1, stream id 0x20.
    payload=bytes([0x80,0x80,5])+bytes(5)+bytes([0x20])+base
    sub=b'\x00\x00\x01\xba'+bytes(10)+b'\x00\x00\x01\xbd'+be16(len(payload))+payload
    (d/'dvd.sub').write_bytes(sub.ljust(2048,b'\xff'))
    (d/'dvd.idx').write_text('size: 720x480\npalette: '+','.join('ffffff' if i else '000000' for i in range(16))+'\nid: en, index: 0\ntimestamp: 00:00:01:000, filepos: 00000000\n')
    run(d/'dvd.idx',d/'dvd.sup','/res:1080p')
    run(d/'dvd.sup',d/'dvd.xml','/res:pal')
    check_xml(d/'dvd.xml')
    # HD-DVD sample with a 768-byte Y/Cr/Cb palette and 256-byte alpha table.
    palette=bytearray([16,128,128]*256);palette[3:6]=bytes([210,128,128])
    alpha=bytearray([255]*256);alpha[1]=0
    cmdbody=bytes([0x83])+palette+bytes([0x84])+alpha+bytes([0x85,0,0,1,0,0,1])+bytes([0x86])+be32(10)+be32(11)+bytes([255])
    # Relative offsets from master=10: even=10 -> absolute 20; odd=11 -> 21; command=12 ->22.
    command=be16(0)+be32(12)+bytes([1])+cmdbody
    total=20+2+len(command)
    packet=b'SP'+struct.pack('<I',90000)+bytes(6)+be32(total-10)+be32(12)+bytes([0x90,0x90])+command
    (d/'hd.sup').write_bytes(packet)
    run(d/'hd.sup',d/'hd.xml','/res:ntsc')
    check_xml(d/'hd.xml')
    run(d/'hd.sup',d/'hd-bd.sup','/res:1080p')
    run(d/'hd-bd.sup',d/'hd-rt.xml')
    check_xml(d/'hd-rt.xml')
    # Explicit malformed input must fail and not emit a valid converted file.
    (d/'bad.sup').write_bytes(data[:29])
    p=subprocess.run([cli,str(d/'bad.sup'),str(d/'bad.xml')],capture_output=True)
    assert p.returncode!=0
print('PASS: PGS->BDN->PGS, VobSub->PGS, HD-DVD->PGS, native PNG, malformed rejection')
