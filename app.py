# media file들 이름을 파일 수정 날짜 XXXX-XX-XX-넘버링.확장자로 변경하는 프로그램입니다.
import os
import time

media_extensions = [".jpg", ".tga", ".png", ".mov", ".avi",
                    ".wmv", ".flv", ".mpg", ".mpeg", ".mp4", ".3gp", ".gif", ".jpeg", ".jfif", ".webp", ".bmp"]


def func(path):
    global media_extensions

    file_list = os.listdir(path)

    date_dict = {}

    for file_name in file_list:
        file_path = path + f"\\{file_name}"

        if os.path.isdir(file_path):
            print(file_name)
            func(file_path)
        else:
            print(f"file_name: {file_name}", end="\t")

            try:
                ext = os.path.splitext(file_path)[1].lower()

                if ext in media_extensions:
                    modified_time = time.localtime(os.stat(file_path).st_mtime)
                    sz_date = "%04d-%02d-%02d" % (modified_time.tm_year,
                                                  modified_time.tm_mon, modified_time.tm_mday)
                    print(f"mtime: {sz_date}", end="\t")

                    if sz_date in date_dict:
                        date_dict[sz_date] += 1
                    else:
                        date_dict[sz_date] = 1

                    new_file_name = f"{sz_date}-{date_dict[sz_date]}{ext}"
                    print(f"new_fname: {new_file_name}")
                    os.rename(file_path, f"{path}\\{new_file_name}")

            except FileExistsError:
                pass

    print("--- --- --- --- ---")


path = input()
# path = "D:\\MEDIA"
# path = "C:\\Users\\jeony\\Downloads\\Guitar"

func(path)
