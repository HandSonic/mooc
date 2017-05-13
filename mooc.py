# -*- coding:utf-8 -*-
import re
import requests
import os
import sys
from utils import mkdir_p, resume_download_file, clean_filename

def main():
    params = raw_input("input params:")
    params = str(params).encode("utf-8")
    username = '535036628@qq.com'
    password = 'aikechengp'
    print "params:%s"  %params
    # if sys.argv[1] is None:
    #     print('缺少用户名参数 e.g. python icourse163.py username password param')
    #     sys.exit(1)
    # if sys.argv[2] is None:
    #     print('缺少密码参数 e.g. python icourse163.py username password param')
    #     sys.exit(1)
    # if sys.argv[3] is None:
    #     print('缺少课程链接参数 e.g. python icourse163.py username password param')
    #     sys.exit(1)
    # NUDT-42003 学校课程id、tid为mooc上课程id
    # course_link = sys.argv[3]
    course_link = params
    path = './'

    course_link_pattern = '(?P<s_course_id>[^/]+)\?tid=(?P<mooc_tid>[^/]+)'
    m = re.match(course_link_pattern, course_link)
    if m is None:
        print('The URL provided is not recognized!')
        sys.exit(0)
    s_course_id = m.group('s_course_id')
    mooc_tid = m.group('mooc_tid')

    path = os.path.join(path, clean_filename(s_course_id))
    # 1.登陆
    login_url = 'http://login.icourse163.org/reg/icourseLogin.do'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6,zh-TW;q=0.4',
        'Connection': 'keep-alive',
        'Referer': 'http://www.icourse163.org/member/login.htm',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    login_data = {
        'returnUrl': 'aHR0cDovL3d3dy5pY291cnNlMTYzLm9yZy9pbmRleC5odG0=',
        'failUrl': 'aHR0cDovL3d3dy5pY291cnNlMTYzLm9yZy9tZW1iZXIvbG9naW4uaHRtP2VtYWlsRW5jb2RlZD1Nek16TXpNeU1qTTE=',
        'savelogin': 'true',
        'oauthType': '',
        'username': username,
        'passwd': password
    }
    web_host = 'www.icourse163.org'

    session = requests.Session()
    session.headers.update(headers)
    session.post(login_url, data=login_data)
    print('Login done...')

    # 2.查看课程信息
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6,zh-TW;q=0.4',
        'Connection': 'keep-alive',
        'Content-Type': 'text/plain',
        'Cookie': 'STUDY_SESS=%s; ' % session.cookies['STUDY_SESS'],
        'Host': web_host,
    }
    params = {
        'callCount': 1,
        'scriptSessionId': '${scriptSessionId}190',
        'httpSessionId': 'e8890caec7fe435d944c0f318b932719',
        'c0-scriptName': 'CourseBean',
        'c0-methodName': 'getLastLearnedMocTermDto',
        'c0-id': 0,
        'c0-param0': 'number:' + mooc_tid,
        'batchId': 434820,  # arbitrarily
    }
    session.headers.update(headers)
    getcourse_url = 'http://www.icourse163.org/dwr/call/plaincall/CourseBean.getLastLearnedMocTermDto.dwr'
    r3 = session.post(getcourse_url, data=params)
    print('Parsing...')

    # Parse Main Page
    syllabus = parse_syllabus_icourse163(session, r3.content)
    # If syllabus exists
    if syllabus:
        print('Done.')
    else:
        print('Failed. No course content on the page.')
        sys.exit(0)

    #print('Save files to %s' % path)
    print_vedio_name(session, syllabus, path)

def print_vedio_name(session, leclist, path=''):
    print "path\n"
    print path
    video_file = open(path + 'vedio.txt', 'wb')
    video_file.truncate()
    for week in leclist:
            cur_week = week[0]
            lessons = week[1]
            for lesson in lessons:
                cur_lesson = lesson[0].encode("utf-8")
                lectures = lesson[1]
                #(link,undef) = lectures
                # print(repr(lessons))
                cur_week = clean_filename(cur_week)
                #print "cur_lesson:%s" %cur_lesson
                video_file.write(cur_lesson)
                video_file.write("\n")
                #print "lectures:"
                #print lectures[0]
                for (lecnum, (lecture_url, lecture_name)) in enumerate(lectures):
                    video_file.write(lecture_url.encode("utf-8"))
                    video_file.write("\n")
    video_file.close()

def parse_syllabus_icourse163(session, page):
    data = page.splitlines(True)
    # video:     contentId       id          name        teremId
    vid_reg = 'contentId=([0-9]+);.+contentType=1;.+id=([0-9]+);.+name=\"(.+)\";.+\.termId=([0-9]+);'
    # doc(pdf):      contentId
    doc_id_reg = 'contentId=([0-9]+);.+contentType=3;'
    # lecture:       name
    lecture_reg = 'contentId=null.+name=\"(.+)\";.+releaseTime='
    # week:      name
    week_reg = 'contentId=null.+lesson=.+name=\"(.+)\";.+releaseTime='

    #  Course.Bean.getLessonUnitLearnVo.dwr
    geturl_url = 'http://www.icourse163.org/dwr/call/plaincall/CourseBean.getLessonUnitLearnVo.dwr'
    # term[[lessonsName, [[url, lectureName]]]]      某学期课名[[某周的课[单节课课]]]
    term = []
    lessons = []
    lectures = []
    cur_week = ''  # weekName
    cur_lesson = ''

    multi_resolution_flag = [
        'mp4ShdUrl',
        'flvShdUrl',
        'mp4HdUrl',
        'mp4SdUrl',
        'flvHdUrl',
        'flvSdUrl', ]

    # Line by line
    for line in data:
        print('.')
        # s1 : Week   (gourp(1) : name)
        s1 = re.search(week_reg, line.decode('utf-8'))

        if s1:
            # term >> lessons >> lectures
            # term [(cur_week, (cur_lesson, lecture_name))]
            # If lecture exists, lessons(cur_lesson, lecture_name)
            if lectures:
                lessons.append((cur_lesson, lectures))
                lectures = []

            if lessons:
                term.append((cur_week, lessons))
                lessons = []
            cur_week = s1.group(1)
            continue
        else:
            # s2 : lecture_reg
            s2 = re.search(lecture_reg, line.decode('utf-8'))
            if s2:
                if lectures:
                    lessons.append((cur_lesson, lectures))
                    lectures = []
                cur_lesson = s2.group(1).encode('latin-1').decode('unicode_escape')
                continue
            else:
                # # video:     1.contentId       2.id        3.videoName      4.teremId
                s3 = re.search(vid_reg, line.decode('utf-8'))
                if s3:
                    lecture_name = s3.group(2)
                    params = {
                        'callCount': 1,
                        'scriptSessionId': '${scriptSessionId}190',  # * , but arbitrarily
                        'httpSessionId': 'e9b42cf7cd92430a9295e0915c584209',
                        'c0-scriptName': 'CourseBean',
                        'c0-methodName': 'getLessonUnitLearnVo',
                        'c0-id': '0',
                        'c0-param0': 'number:' + s3.group(1),  # contentId
                        'c0-param1': 'number:1',
                        'c0-param2': 'number:0',
                        'c0-param3': 'number:' + s3.group(2),  # id
                        'batchId': str(1451101151271),  # * , but arbitrarily
                    }
                    r = session.post(geturl_url, data=params, cookies=session.cookies)

                    s4 = re.search("//#DWR-REPLY\s+(\w.*)\s+", r.content.decode('utf-8'))
                    info = dict(re.findall("(\w+)=\"(.*?)\";", s4.group(1)))
                    lecture_url = ''
                    for res in multi_resolution_flag:
                        if (res in info) and (info[res] != 'null'):
                            lecture_url = info[res].strip('\"')
                            break
                    if '' != lecture_url:
                        lectures.append((lecture_url, lecture_name))
                    continue

    if len(lectures) > 0:
        lessons.append((cur_lesson, lectures))
    if len(lessons) > 0:
        term.append((cur_week, lessons))

    return term


if __name__ == '__main__':
    main()