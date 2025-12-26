from main import JishoSearcher

def test():
    test = JishoSearcher(lang="zh")
    test.search_print("！＊｛５ー｝＆＜あ＞＊｛１ー３｝「！o」い")
    # print(test._process_normal("Aああ@あ*{1-3}ああO"))
    # test.search_print("A\"D;|A|=2")
    # test.search_print("A\"BA\'B;|A|=1;|B|=1")
    # test.search_print("AC\";ACC", num=10)
    # test.search_print("CA;C;A?[o];ACB;(((AB?[C])));|A|=2;|B|=2;|C|=2")
    # test.search_print("A;B;AB?ま",num=20)
    # test.search_print("A;B;AB\"") # Test "
    # test.search_print("AB?ま;A;B") # Test '
    # test.search_print("AA;！＊｛５ー｝＆＜あ＞＊｛１ー３｝「！o」い")
    # test.search_print("ACB;CAB;ACAB;ABC\";|A|=1;|B|=1;|C|=1") 
    # test.search_print("づり?い")
    # test.search_print("AB\";A\"B\";|B|=1")
    functions = [["FUNCA", "あいうえお","かきくけこ"], ["FUNCB", "さしすせそ", "たちつてと"]]
    # test.search_print("FUNCA(A)D;|A|=2", functions = functions)
    test.search_print("は?どけい")#, functions = functions)