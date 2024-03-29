from __future__ import annotations

import binascii
import hashlib
import io
import mimetypes
import os
import types
from typing import Literal, AnyStr, Optional

import aiofiles
import aiofiles.os

READ_MODES = Literal['r', 'rb', 'rt']
WRITE_MODES = Literal['w', 'w+', 'wb', 'wb+', 'wt', 'wt+']


async def read_file_chunks(
        path,
        chunk_size=32768,
        mode: READ_MODES = 'rb',
        start_index: Optional[int] = None,
        end_index: Optional[int] = None):
    async with aiofiles.open(path, mode) as f:
        remaining_size = None
        if start_index is not None:
            await f.seek(start_index)
            if end_index is not None:
                remaining_size = end_index-start_index+1
                if remaining_size < chunk_size:
                    chunk_size = remaining_size
        elif end_index is not None:
            remaining_size = end_index+1
            if remaining_size < chunk_size:
                chunk_size = remaining_size
        while chunk := await f.read(chunk_size):
            yield chunk
            if remaining_size is not None:
                remaining_size -= chunk_size
                if remaining_size < chunk_size:
                    chunk_size = remaining_size


async def read_file(
        path,
        mode: READ_MODES = 'rb',
        start_index: Optional[int] = None,
        end_index: Optional[int] = None):
    async with aiofiles.open(path, mode) as f:
        if start_index:
            await f.seek(start_index)
            if end_index:
                return await f.read(end_index-start_index+1)
        elif end_index:
            return await f.read(end_index+1)
        return await f.read()


async def read_file_lines(path, mode: READ_MODES = 'rb'):
    async with aiofiles.open(path, mode) as f:
        return await f.readlines()


async def write_file(data, dir_path, name, chunk_size=32768, mode: WRITE_MODES = 'wb+'):
    if not os.path.isdir(dir_path):
        await aiofiles.os.makedirs(dir_path)
    path = os.path.join(dir_path, name)
    async with aiofiles.open(path, mode) as f:
        if isinstance(data, types.AsyncGeneratorType):
            async for chunk in data:
                await f.write(chunk)
        elif isinstance(data, types.GeneratorType):
            for chunk in data:
                await f.write(chunk)
        elif isinstance(data, aiofiles.threadpool.binary.AsyncBufferedIOBase):
            while chunk := await data.read(chunk_size):
                await f.write(chunk)
        elif isinstance(data, io.IOBase):
            while chunk := data.read(chunk_size):
                await f.write(chunk)
        else:
            await f.write(data)
    return os.path.isfile(path)


async def move_file(src_dir_path, dst_dir_path, name):
    src_file_path = os.path.join(src_dir_path, name)
    if not os.path.isfile(src_file_path):
        return False
    if not os.path.isdir(dst_dir_path):
        await aiofiles.os.makedirs(dst_dir_path)
    dst_file_path = os.path.join(dst_dir_path, name)
    await aiofiles.os.replace(src_file_path, dst_file_path)
    return os.path.isfile(dst_file_path)


async def rename_file(dir_path, old_name, new_name):
    file_path = os.path.join(dir_path, old_name)
    if not os.path.isfile(file_path):
        return False
    renamed_file_path = os.path.join(dir_path, new_name)
    await aiofiles.os.rename(file_path, renamed_file_path)
    return os.path.isfile(renamed_file_path)


async def remove_file(path):
    if os.path.isfile(path):
        await aiofiles.os.remove(path)
        return not os.path.exists(path)
    return False


async def remove_dir(path):
    if os.path.isdir(path):
        await aiofiles.os.rmdir(path)
        return not os.path.exists(path)
    return False


async def remove_tree(path):
    if os.path.isdir(path):
        for i in os.listdir(path):
            await remove_tree(os.path.join(path, i))
        await aiofiles.os.rmdir(path)
        return not os.path.exists(path)
    elif os.path.isfile(path):
        await aiofiles.os.remove(path)
        return not os.path.exists(path)
    return False


async def get_checksum(data=b'', path=None, chunk_size=32768):
    h = hashlib.blake2b()
    if path:
        async with aiofiles.open(path, 'rb') as f:
            while chunk := await f.read(chunk_size):
                h.update(chunk)
    elif isinstance(data, types.AsyncGeneratorType):
        async for chunk in data:
            h.update(chunk)
    elif isinstance(data, types.GeneratorType):
        for chunk in data:
            h.update(chunk)
    elif isinstance(data, aiofiles.threadpool.binary.AsyncBufferedIOBase):
        while chunk := await data.read(chunk_size):
            h.update(chunk)
    elif isinstance(data, io.IOBase):
        while chunk := data.read(chunk_size):
            h.update(chunk)
    else:
        h.update(data)
    return h.hexdigest()


async def write_file_and_get_checksum(data, dir_path, name, chunk_size=32768, mode: WRITE_MODES = 'wb+'):
    if not os.path.isdir(dir_path):
        await aiofiles.os.makedirs(dir_path)
    path = os.path.join(dir_path, name)
    h = hashlib.blake2b()
    async with aiofiles.open(path, mode) as f:
        if isinstance(data, types.AsyncGeneratorType):
            async for chunk in data:
                await f.write(chunk)
                h.update(chunk)
        elif isinstance(data, types.GeneratorType):
            for chunk in data:
                await f.write(chunk)
                h.update(chunk)
        elif isinstance(data, aiofiles.threadpool.binary.AsyncBufferedIOBase):
            while chunk := await data.read(chunk_size):
                await f.write(chunk)
                h.update(chunk)
        elif isinstance(data, io.IOBase):
            while chunk := data.read(chunk_size):
                await f.write(chunk)
                h.update(chunk)
        else:
            await f.write(data)
            h.update(data)
    if os.path.isfile(path):
        return h.hexdigest()
    return None


async def get_file_size(path):
    return await aiofiles.os.path.getsize(path)


def get_human_readable_size(size, precision=1):
    for suffix in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return '%.*f%s' % (precision, size, suffix)
        size /= 1024.0
    return '%.*f%s' % (precision, size, 'TB')


def get_extension(filename: AnyStr) -> AnyStr:
    _, ext = os.path.splitext(filename)
    return ext[1:].lower()


def get_suffix_mimetype(filename):
    type, encoding = mimetypes.guess_type(filename)
    return type


def get_extension_mimetype(extension):
    return mimetypes.types_map.get(f'.{extension}')


def get_type(value) -> list[str] | None:
    if not value:
        raise Exception('file text content error')
    # Binery files signatures list
    type_signs = [
        # image
        (['jpeg', 'jpg'],
         [(0, b'ffd8ffe0'), (0, b'ffd8ffe1'), (0, b'ffd8ffe2'), (0, b'ffd8ffe3'), (0, b'ffd8ffe8'), (0, b'ffd8ffdb')]),
        # jpe,jfif
        (['png'], [(0, b'89504e470d0a1a0a', -16, b'49454e44ae426082')]),
        (['bmp'], [(0, b'424d')]),  # dib
        (['gif'], [(0, b'474946383761'), (0, b'474946383961')]),
        (['tiff', 'tif'], [(0, b'492049'), (0, b'49492a00'), (0, b'4d4d002a'), (0, b'4d4d002b')]),
        (['jp2'], [(0, b'0000000c6a5020200d0a')]),
        (['rgb'], [(0, b'01da01010003')]),
        (['rast'], [(0, b'59a66a95')]),
        (['xbm'], [(0, b'23646566696e6520')]),
        (['pbm'], [(0, b'503120'), (0, b'503109'), (0, b'50310a'), (0, b'50310d'), (0, b'503420'), (0, b'503409'),
                   (0, b'50340a'), (0, b'50340d')]),
        (['pgm'], [(0, b'503220'), (0, b'503209'), (0, b'50320a'), (0, b'50320d'), (0, b'503520'), (0, b'503509'),
                   (0, b'50350a'), (0, b'50350d')]),
        (['ppm'], [(0, b'503320'), (0, b'503309'), (0, b'50330a'), (0, b'50330d'), (0, b'503620'), (0, b'503609'),
                   (0, b'50360a'), (0, b'50360d')]),
        (['heic'], [(8, b'6674797068656963'), (8, b'6674797068656978'), (8, b'667479706865696d'),
                    (8, b'6674797068656973'), (8, b'667479706d696631')]),
        # video
        (['mpeg', 'mpg'], [(0, b'000001b3')]),
        (['mpeg', 'mpg', 'vob'], [(0, b'000001ba')]),
        (['mp4'], [(8, b'6674797069736f6d'), (8, b'6674797033677035'), (8, b'667479704d534e56'),
                   (8, b'667479706d703432'), (8, b'667479704d345620')]),
        # Todo: (['m4v'], [(8, b'667479706d703432'), (8, b'667479704d345620')]),
        (['avi'], [(0, b'52494646', 16, b'415649204c495354')]),
        (['asf', 'wmv', 'wma'], [(0, b'3026b2758e66cf11a6d900aa0062ce6c')]),
        (['mov'], [(8, b'6674797071742020'), (8, b'6d6f6f76'), (8, b'66726565'), (8, b'6d646174'),
                   (8, b'77696465'), (8, b'706e6f74'), (8, b'736b6970')]),
        (['3gp'], [(0, b'0000001466747970336770')]),
        (['3g2'], [(0, b'0000002066747970336770')]),
        (['flv'], [(0, b'464c5601')]),
        (['swf'], [(0, b'435753'), (0, b'465753'), (0, b'5a5753')]),
        (['ogg', 'ogv', 'oga', 'ogx'], [(0, b'4f67675300020000000000000000')]),
        (['rmvb', 'rm'], [(0, b'2e524d46')]),
        (['ivr'], [(0, b'2e524543')]),
        (['mkv'], [(0, b'1a45dfa393428288')]),
        (['webm'], [(0, b'1a45dfa3')]),
        (['ts', 'tsv', 'tsa'], [(0, b'47', 376, b'47')]),
        (['hevc'], [(8, b'6674797068657663'), (8, b'6674797068657678'), (8, b'667479706865766d'),
                    (8, b'6674797068657673'), (8, b'667479706d736631')]),
        # audio
        (['wave', 'wav'], [(0, b'52494646', 16, b'57415645666d7420')]),
        (['mp3'], [(0, b'494433')]),
        (['ra'], [(0, b'2e524d460000001200'), (0, b'2e7261fd00')]),
        (['midi', 'mid'], [(0, b'4d546864')]),
        (['cda'], [(0, b'52494646', 16, b'43444441666d7420')]),
        (['rmi'], [(0, b'52494646', 16, b'524d494464617461')]),
        (['amr'], [(0, b'2321414d52')]),
        (['aac'], [(0, b'fff1'), (0, b'fff9')]),
        (['m4a'], [(0, b'00000020667479704d3441')]),
        (['aiff'], [(0, b'464f524d00')]),
        (['caf'], [(0, b'63616666')]),
        (['adx'], [(0, b'80000020031204')]),  # other adx
        (['nsf'], [(0, b'4e45534d1a01')]),  # other nsf
        # graphic
        (['psd'], [(0, b'38425053')]),
        (['xcf'], [(0, b'67696d702078636620')]),
        (['psp'], [(0, b'7e424b00')]),
        # document
        (['pdf'], [(0, b'25504446', -12, b'0a2525454f46'), (0, b'25504446', -14, b'0a2525454f460a'),
                   (0, b'25504446', -18, b'0d0a2525454f460d0a'), (0, b'25504446', -14, b'0d2525454f460d')]),
        # (FIXME: match .ai)
        # font
        (['ttf'], [(0, b'0001000000')]),
        # archive
        (['rar'], [(0, b'526172211a07')]),
        (['tar'], [(514, b'7573746172')]),
        (['z'], [(0, b'1f9d90'), (0, b'1fa0')]),  # tar.z
        (['bz2', 'tbz2', 'tb2'], [(0, b'425a68')]),  # bz2,tar.bz2
        (['7z'], [(0, b'377abcaf271c')]),
        (['xz'], [(0, b'fd377a585a00')]),
        (['gz', 'tgz'], [(0, b'1f8b08')]),  # (FIXME: match .vlt)
        (['zip'], [(0, b'504b0304', -44, b'504b0506', -4, b'0000'), (0, b'504b0304', -44, b'504b0606', -4, b'0000'),
                   (0, b'504b0304', -44, b'504b0607', -4, b'0000'), (0, b'504b0506'), (0, b'504b0708'),
                   (0, b'504b030414000100630000000000'), (60, b'504b4c495445'), (1052, b'504b537058'),
                   (58304, b'57696e5a6970')]),
        (['iso'], [(0, b'4344303031')]),
        # TODO: .odt
    ]

    # Plain text file checkers
    type_checkers = []

    def check_xml(value):
        from xml.etree import ElementTree as et
        try:
            tree = et.ElementTree(et.fromstring(value))
        except:
            return False
        # svg
        try:
            tag = None
            for event, el in tree.iter():
                tag = el.tag
                break
            if tag and tag.startswith('{http://www.w3.org/2000/svg}'):
                return ['svg']
        except:
            pass
        # xml
        return ['xml']

    type_checkers.append(check_xml)

    # Zip wrapped file checker
    def check_zip_wrapped(value):
        # odt: when unzip: mimetype file content: application/vnd.oasis.opendocument.text
        # docx: when unzip: [Content_Types].xml content: application/vnd.openxmlformats
        # -officedocument.wordprocessingml.document.main+xml
        # zip
        return ['zip']

    # Convert to hex
    h = binascii.hexlify(value)

    # Check major binary files
    for typ in type_signs:
        for sign in typ[1]:
            matched = False
            for i in range(int(len(sign) / 2)):
                index = i * 2
                try:
                    if h[sign[index]:].startswith(sign[index + 1]):
                        matched = True
                    else:
                        matched = False
                        break
                except IndexError:
                    matched = False
                    break
            if matched:
                if typ[0] == ['zip']:
                    return check_zip_wrapped(value)
                else:
                    return typ[0]

    # Check major text files
    else:
        for func in type_checkers:
            result = func(value)
            if result:
                return result
    return None
