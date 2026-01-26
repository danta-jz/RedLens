//
//  Match.swift
//  RedLens
//
//  Created by 贾真 on 2026/1/14.
//

import SwiftUI
internal import Combine

struct Match: Codable, Identifiable {
    var id: String { date + opponent }
    
    let date: String
    let time: String
    let opponent: String
    let competition: String
    let status: String  // "U"=未赛, "C"=完赛
    let score: String
    let isHome: Bool
    let schemeUrl: String
    
    enum CodingKeys: String, CodingKey {
        case date, time, opponent, competition, status, score
        case isHome = "is_home"
        case schemeUrl = "scheme_url"
    }
    
    // MARK: - 1. 初始化
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        date = try container.decode(String.self, forKey: .date)
        time = try container.decode(String.self, forKey: .time)
        opponent = try container.decode(String.self, forKey: .opponent)
        status = try container.decode(String.self, forKey: .status)
        isHome = try container.decode(Bool.self, forKey: .isHome)
        
        score = try container.decodeIfPresent(String.self, forKey: .score) ?? ""
        competition = try container.decodeIfPresent(String.self, forKey: .competition) ?? "Premier League"
        schemeUrl = try container.decodeIfPresent(String.self, forKey: .schemeUrl) ?? ""
    }
    
    // 手动初始化 (兼容 Preview)
    init(date: String, time: String, opponent: String, competition: String = "Premier League", status: String, score: String, isHome: Bool, schemeUrl: String = "") {
        self.date = date
        self.time = time
        self.opponent = opponent
        self.competition = competition
        self.status = status
        self.score = score
        self.isHome = isHome
        self.schemeUrl = schemeUrl
    }
    
    // MARK: - 2. 逻辑属性
    var isFinished: Bool { status == "C" }
    
    // ⚠️ 修改点：强制返回 true，让界面认为所有比赛都有录像
    var hasAction: Bool {
        return true
    }
    
    var dateObject: Date? {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.date(from: date)
    }
}

// MARK: - 3. 时区转换核心 (伦敦 -> 北京)
extension Match {
    private var realDate: Date? {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd HH:mm"
        formatter.timeZone = TimeZone(identifier: "Europe/London")
        return formatter.date(from: "\(date) \(time)")
    }
    
    var bjTime: String {
        guard let date = realDate else { return time }
        let formatter = DateFormatter()
        formatter.dateFormat = "HH:mm"
        formatter.timeZone = TimeZone(identifier: "Asia/Shanghai")
        return formatter.string(from: date)
    }
    
    var bjDate: String {
        guard let date = realDate else { return date }
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd"
        formatter.timeZone = TimeZone(identifier: "Asia/Shanghai")
        return formatter.string(from: date)
    }
}

// MARK: - 4. 汉化扩展
extension Match {
    var homeTeamNameCN: String { isHome ? "阿森纳" : TeamTranslator.translate(opponent) }
    var awayTeamNameCN: String { isHome ? TeamTranslator.translate(opponent) : "阿森纳" }
    
    var competitionNameCN: String {
        switch competition {
        case "Premier League": return "英超"
        case "UEFA Champions League": return "欧冠"
        case "FA Cup": return "足总杯"
        case "League Cup": return "联赛杯"
        case "Community Shield": return "社区盾"
        case "Friendly": return "友谊赛"
        default: return competition
        }
    }
}

// MARK: - 5. 翻译字典
struct TeamTranslator {
    static func translate(_ name: String) -> String {
        return dict[name] ?? name
    }
    private static let dict: [String: String] = [
        "Arsenal": "阿森纳", "Aston Villa": "阿斯顿维拉", "Bournemouth": "伯恩茅斯", "Brentford": "布伦特福德", "Brighton & Hove Albion": "布莱顿", "Burnley": "伯恩利", "Chelsea": "切尔西", "Crystal Palace": "水晶宫", "Everton": "埃弗顿", "Fulham": "富勒姆", "Leeds United": "利兹联", "Leicester City": "莱斯特城", "Liverpool": "利物浦", "Luton Town": "卢顿", "Manchester City": "曼城", "Manchester United": "曼联", "Newcastle United": "纽卡斯尔联", "Nottingham Forest": "诺丁汉森林", "Sheffield United": "谢菲尔德联", "Southampton": "南安普顿", "Tottenham Hotspur": "托特纳姆热刺", "West Ham United": "西汉姆联", "Wolverhampton Wanderers": "狼队", "Wolves": "狼队",
        "Ipswich Town": "伊普斯维奇", "Norwich City": "诺维奇", "Watford": "沃特福德", "West Bromwich Albion": "西布朗", "Middlesbrough": "米德尔斯堡", "Coventry City": "考文垂", "Sunderland": "桑德兰", "Blackburn Rovers": "布莱克本", "Hull City": "赫尔城", "Preston North End": "普雷斯顿", "Bristol City": "布里斯托尔城", "Cardiff City": "加的夫城", "Swansea City": "斯旺西", "Stoke City": "斯托克城", "QPR": "女王公园巡游者", "Queens Park Rangers": "女王公园巡游者", "Birmingham City": "伯明翰", "Huddersfield Town": "哈德斯菲尔德", "Rotherham United": "罗瑟勒姆", "Millwall": "米尔沃尔", "Plymouth Argyle": "普利茅斯", "Sheffield Wednesday": "谢周三", "Portsmouth": "朴茨茅斯", "Derby County": "德比郡", "Bolton Wanderers": "博尔顿", "Barnsley": "巴恩斯利", "Charlton Athletic": "查尔顿", "Reading": "雷丁", "Wigan Athletic": "威根竞技", "Blackpool": "布莱克浦", "Peterborough United": "彼得堡联", "Oxford United": "牛津联", "Lincoln City": "林肯城", "Port Vale": "韦尔港", "Shrewsbury Town": "什鲁斯伯里", "Exeter City": "埃克塞特城", "Wycombe Wanderers": "威科姆", "Leyton Orient": "莱顿东方", "Wrexham": "雷克瑟姆",
        "Real Madrid": "皇家马德里", "FC Barcelona": "巴塞罗那", "Barcelona": "巴塞罗那", "Atletico Madrid": "马德里竞技", "Sevilla": "塞维利亚", "Real Sociedad": "皇家社会", "Villarreal": "比利亚雷亚尔", "Real Betis": "皇家贝蒂斯", "Athletic Club": "毕尔巴鄂竞技", "Girona": "赫罗纳", "Valencia": "瓦伦西亚",
        "Bayern Munich": "拜仁慕尼黑", "Borussia Dortmund": "多特蒙德", "RB Leipzig": "莱比锡红牛", "Bayer Leverkusen": "勒沃库森", "Eintracht Frankfurt": "法兰克福", "Wolfsburg": "沃尔夫斯堡", "Stuttgart": "斯图加特", "Borussia Monchengladbach": "门兴格拉德巴赫",
        "Inter Milan": "国际米兰", "AC Milan": "AC米兰", "Milan": "AC米兰", "Juventus": "尤文图斯", "Napoli": "那不勒斯", "Roma": "罗马", "Lazio": "拉齐奥", "Atalanta": "亚特兰大", "Fiorentina": "佛罗伦萨", "Bologna": "博洛尼亚",
        "Paris Saint-Germain": "巴黎圣日耳曼", "PSG": "巴黎圣日耳曼", "Monaco": "摩纳哥", "Lyon": "里昂", "Marseille": "马赛", "Lens": "朗斯", "Lille": "里尔", "Nice": "尼斯", "Rennes": "雷恩",
        "Benfica": "本菲卡", "Porto": "波尔图", "Sporting CP": "葡萄牙体育", "Braga": "布拉加", "Ajax": "阿贾克斯", "PSV Eindhoven": "埃因霍温", "Feyenoord": "费耶诺德", "Celtic": "凯尔特人", "Rangers": "流浪者", "Shakhtar Donetsk": "顿涅茨克矿工", "Dynamo Kyiv": "基辅迪纳摩", "Galatasaray": "加拉塔萨雷", "Fenerbahce": "费内巴切", "Besiktas": "贝西克塔斯", "Red Bull Salzburg": "萨尔茨堡红牛", "Slavia Prague": "布拉格斯拉维亚", "Sparta Prague": "布拉格斯巴达", "Viktoria Plzen": "比尔森胜利", "Olympiacos": "奥林匹亚科斯", "Panathinaikos": "帕纳辛奈科斯", "PAOK": "PAOK萨洛尼卡", "AEK Athens": "雅典AEK", "Club Brugge": "布鲁日", "Anderlecht": "安德莱赫特", "Genk": "根克", "Union Saint-Gilloise": "圣吉罗斯联合", "Kairat": "凯拉特", "Young Boys": "伯尔尼年轻人", "FC Zurich": "苏黎世", "Basel": "巴塞尔", "Dinamo Zagreb": "萨格勒布迪纳摩", "Copenhagen": "哥本哈根", "Midtjylland": "中日德兰"
    ]
}

// MARK: - 6. 数据仓库
class MatchStore: ObservableObject {
    @Published var matches: [Match] = []
    @Published var lastFinishedMatch: Match? = nil
    @Published var nextMatch: Match? = nil
    @Published var futureMatches: [Match] = []
    @Published var defaultHomeTab: Int = 1
    
    private let remoteURL = "https://raw.githubusercontent.com/danta-jz/redlens/main/matches_with_videos.json"
    
    init() {
        loadLocalData()
        fetchRemoteData()
    }
    
    func loadLocalData() {
        guard let url = Bundle.main.url(forResource: "matches_with_videos", withExtension: "json"),
              let data = try? Data(contentsOf: url) else { return }
        decodeAndAssign(data)
    }
    
    func fetchRemoteData() {
        guard let url = URL(string: remoteURL) else { return }
        URLSession.shared.dataTask(with: URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData)) { [weak self] data, _, _ in
            if let data = data { DispatchQueue.main.async { self?.decodeAndAssign(data) } }
        }.resume()
    }
    
    private func decodeAndAssign(_ data: Data) {
        let decoder = JSONDecoder()
        if let allMatches = try? decoder.decode([Match].self, from: data) {
            self.matches = allMatches
            self.processMatches()
        }
    }
    
    private func processMatches() {
        let finished = matches.filter { $0.isFinished }.sorted { $0.date < $1.date }
        let upcoming = matches.filter { !$0.isFinished }.sorted { $0.date < $1.date }
        self.lastFinishedMatch = finished.last
        self.nextMatch = upcoming.first
        self.futureMatches = Array(upcoming.prefix(3))
        
        if let lastMatch = self.lastFinishedMatch, let matchDate = lastMatch.dateObject {
            self.defaultHomeTab = (Date().timeIntervalSince(matchDate) / 3600) < 48 ? 0 : 1
        } else {
            self.defaultHomeTab = 1
        }
    }
}
