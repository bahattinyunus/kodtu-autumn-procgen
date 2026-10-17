using System;
using System.Collections.Generic;

namespace AutumnProcGen.Core
{
    [Serializable]
    public class InscriptionData
    {
        public string Title;
        public string Content;

        public InscriptionData(string title, string content)
        {
            Title = title;
            Content = content;
        }
    }

    [Serializable]
    public class AchievementData
    {
        public string Key;
        public string Title;
        public string Description;
        public string Icon;

        public AchievementData(string key, string title, string description, string icon)
        {
            Key = key;
            Title = title;
            Description = description;
            Icon = icon;
        }
    }

    public static class StoryData
    {
        public static readonly InscriptionData[] Inscriptions = new InscriptionData[]
        {
            new InscriptionData(
                "1961 KEMAL KURDAS VE ILK AGAC BAYRAMI",
                "\"3 Aralik 1961... Rektor Kemal Kurdas onderliginde binlerce ODTU ogrencisi ve hocasi bozkira indi. " +
                "Yalincak sirtlarina ilk fidanlar dikildiginde herkes bunun imkansiz bir hayal oldugunu soylemisti. " +
                "O gun dikilen her fidan, aklin ve bilimin bozkir entropisine meydan okuyusu oldu.\" (+15 Isi & Ilham Hizi)"
            ),
            new InscriptionData(
                "YALINCAK HOYUGU VE KADIM ANADOLU MIRASI",
                "\"Bu topraklar sadece bir universite kampusu degil; binlerce yildir Hititlerden Friglere uzanan kadim bir hafizadir. " +
                "ODTU arkeologlarinin Yalincak Hoyugu'nde gun yuzune cikardigi canak comlekler der ki: " +
                "Insan gecer, nesiller donusur; geriye yalnizca topraga birakilan emek ve bilgelik kalir.\" (+15 Isi & Ilham Hizi)"
            ),
            new InscriptionData(
                "EYMIR GOLU VE BOZKIRDAKI MAVI GERDANLIK",
                "\"Ankara'nin corak tepeleri arasina saklanmis Eymir, sabah ayazinda antrenman yapan ODTU kurekcilerinin ve " +
                "gocmen kuslarin siginagidir. Suya vuran her kurek sesi, dogayla savasmak yerine onun ritmine uymanin " +
                "en saf siiridir.\" (+15 Isi & Ilham Hizi)"
            ),
            new InscriptionData(
                "1968 DEVRIM STADYUMU VE OZGURLUK RUHU",
                "\"Stadyum basamaklarina boydan boya kazinan o tek kelime, zamanin ve ruzgarin asindiramadigi bir kolektif " +
                "irade manifestosudur. Bu yazi tasin degil, bagimsizliga ve sorgulayan zihne adanmis bir gencligin ruhuna kazinmistir.\" (+15 Isi & Ilham Hizi)"
            ),
            new InscriptionData(
                "1989 ODTU BILGISAYAR TOPLULUGU (CCLUB)",
                "\"1989 yilinda ODTU koridorlarinda bir araya gelen bilisim tutkunlari, Turkiye'nin ilk ogrenci bilgisayar toplulugunu kurdu. " +
                "Geleneksel KODTU maratonlariyla algoritmalari sanata, kodlari ormanin nefesine donusturen bu mesale, " +
                "bilginin ozgurce paylasildigi her terminalde bugun de parildar.\" (+15 Isi & Ilham Hizi)"
            ),
            new InscriptionData(
                "BOZKIRIN MUHENDISLIK FELSEFESI",
                "\"En saglam sistemler, doganin sadeligini ve zarafetini algoritmalara naksedenlerdir. " +
                "Kodu temiz yaz, dogaya saygi duy, bozkirin her cakil tasinda bir gelecek gor.\" (+15 Isi & Ilham Hizi)"
            )
        };

        public static readonly AchievementData[] Achievements = new AchievementData[]
        {
            new AchievementData("FIRST_DEFLECT", "CELIK & YANSITMA", "Dusman golge kuresini kilicla geri yansit", "⚡"),
            new AchievementData("COMPANION_FRIEND", "KAMPUSUN SADIK DOSTU", "Bozkir Kangali yoldasini sevip moral bul", "🐾"),
            new AchievementData("BILIM_CEREMONY", "1956 BILIM MESALESI", "ODTU Bilim Agaci Aniti ayinini harlayarak zafere ulas", "✦"),
            new AchievementData("CHRONICLE_HISTORIAN", "KADIM HAFIZA", "ODTU Tarihsel Kitabelerinden en az 3 tanesini oku", "📜")
        };
    }
}
