"""Skill knowledge base for semantic requirement matching.

The job catalogue (EMASCO/MASCO, with O*NET-style skill and tool names) often
asks for a general capability such as "Machine Learning", "CI/CD tools" or
"Network monitoring tools", while resumes usually name the specific products a
student used, such as TensorFlow, Jenkins or Wireshark. Exact keyword matching
therefore reports skills as missing although the resume proves them.

Each concept below links catalogue wording (triggers) to specific skills that
prove it (evidence). The relation is one-directional: a specific tool proves
the general capability, but the general capability never proves a specific
tool, and one tool never proves another (Java is not evidence of Python).

Only clearly technical CS/IT evidence is listed. General office software, CAD
and words with an everyday meaning (for example "Chef", "Autopsy" or
"Volatility") are left out so that resumes from other fields do not gain CS
evidence. Words that are only technical when written in a certain way are
matched case-sensitively with a pattern instead (for example "Node.js", not
"node").

Trigger syntax: a trigger is a phrase that must appear in the requirement text
(compared after lower-casing and replacing punctuation with spaces). A trigger
that starts with "=" must equal the whole requirement text.
"""

from __future__ import annotations

from typing import NamedTuple

SKILL_KNOWLEDGE_VERSION = "1.0"


class SkillConcept(NamedTuple):
    name: str
    triggers: tuple[str, ...]
    evidence: tuple[str, ...] = ()
    # (display name, case-sensitive regular expression) for ambiguous words.
    patterns: tuple[tuple[str, str], ...] = ()


_REACT = ("React", r"\bReact(?:\.js|JS)?\b")
_NODE = ("Node.js", r"\bNode(?:\.js|JS)\b")
_EXPRESS = ("Express.js", r"\bExpress(?:\.js|JS)\b")
_UNITY = ("Unity", r"\bUnity(?:3D|\s3D|\sEngine)?\b")
_SWIFT = ("Swift", r"\bSwift(?:UI)?\b")
_ISO_27001 = ("ISO/IEC 27001", r"\bISO(?:/IEC)?\s?27001\b")
_ANGULAR = ("Angular", r"\bAngular(?:JS|\.js)?\b")
_BOOTSTRAP = ("Bootstrap", r"\bBootstrap\b")
_JEST = ("Jest", r"\bJest\b")
_SELENIUM = ("Selenium", r"\bSelenium\b")
_BLENDER = ("Blender", r"\bBlender\b")
_FLASK = ("Flask", r"\bFlask\b")
_HIBERNATE = ("Hibernate", r"\bHibernate\b")
_SCRUM = ("Scrum", r"\bScrum\b")
_RESTFUL = ("RESTful", r"(?i)\brestful\b")
_PANDAS = ("pandas", r"\b[Pp]andas\b")
_IT_SUPPORT = ("IT support", r"\bIT\s(?:[Ss]upport|[Hh]elp\s?[Dd]esk|[Hh]elpdesk)\b")

_CI_CD_TOOLS = (
    "Jenkins",
    "GitHub Actions",
    "GitLab CI",
    "GitLab CI/CD",
    "CircleCI",
    "Travis CI",
    "Azure DevOps",
    "Azure Pipelines",
    "Bitbucket Pipelines",
    "Argo CD",
    "ArgoCD",
    "TeamCity",
    "continuous integration",
    "continuous delivery",
    "continuous deployment",
)
_RELATIONAL_DATABASES = (
    "MySQL",
    "PostgreSQL",
    "Postgres",
    "SQL Server",
    "Microsoft SQL Server",
    "MSSQL",
    "Oracle Database",
    "MariaDB",
    "SQLite",
)
_DATABASE_ADMINISTRATION = (
    "database administration",
    "database administrator",
    "DBA",
    "Oracle DBA",
    "SQL Server Management Studio",
    "SSMS",
    "performance tuning",
    "query optimization",
    "query optimisation",
    "index tuning",
    "database backup",
    "database replication",
    "database migration",
)
_DATABASE_DESIGN = (
    "database design",
    "entity relationship diagram",
    "ERD",
    "database normalization",
    "database normalisation",
    "schema design",
    "data modelling",
    "data modeling",
)
_FRONT_END = (
    "Vue.js",
    "Svelte",
    "Next.js",
    "Nuxt.js",
    "HTML",
    "CSS",
    "Tailwind CSS",
    "Sass",
    "SCSS",
    "jQuery",
    "TypeScript",
    "JavaScript",
)
_FRONT_END_PATTERNS = (_REACT, _ANGULAR, _BOOTSTRAP)
_DESIGN_TOOLS = ("Figma", "Adobe XD", "InVision", "Balsamiq", "Axure")
_TESTING_TOOLS = (
    "JUnit",
    "TestNG",
    "pytest",
    "JMeter",
    "LoadRunner",
    "Appium",
    "Katalon",
    "SoapUI",
    "BrowserStack",
    "unit testing",
    "integration testing",
    "regression testing",
    "test automation",
    "manual testing",
    "user acceptance testing",
    "test cases",
    "test plans",
    "ISTQB",
)

SKILL_CONCEPTS: tuple[SkillConcept, ...] = (
    # Data science and artificial intelligence
    SkillConcept(
        "Machine learning",
        ("Machine Learning", "machine learning models", "machine learning model"),
        (
            "TensorFlow",
            "PyTorch",
            "Keras",
            "scikit-learn",
            "sklearn",
            "XGBoost",
            "LightGBM",
            "CatBoost",
            "Hugging Face",
            "deep learning",
            "neural network",
            "neural networks",
            "random forest",
            "unsupervised learning",
            "natural language processing",
            "computer vision",
            "OpenCV",
            "MLflow",
        ),
    ),
    SkillConcept(
        "Artificial intelligence",
        ("Artificial Intelligence",),
        (
            "machine learning",
            "deep learning",
            "natural language processing",
            "computer vision",
            "TensorFlow",
            "PyTorch",
            "Keras",
            "generative AI",
            "large language model",
            "large language models",
            "OpenAI",
            "LangChain",
        ),
    ),
    SkillConcept(
        "Model deployment",
        ("Model Deployment",),
        ("MLOps", "MLflow", "Kubeflow", "SageMaker", "Vertex AI", "TensorFlow Serving", "TorchServe", "BentoML", "ONNX", "model serving"),
    ),
    SkillConcept(
        "Data science",
        ("Data Science",),
        ("NumPy", "SciPy", "scikit-learn", "Jupyter", "Jupyter Notebook", "machine learning", "statistical modelling", "statistical modeling", "Kaggle"),
        (_PANDAS,),
    ),
    SkillConcept(
        "Data analysis",
        ("Data Analysis", "Data analytics", "Analytics", "Business Data Analysis"),
        ("NumPy", "SPSS", "Stata", "Power BI", "Tableau", "R programming", "RStudio", "data analysis"),
        (_PANDAS,),
    ),
    SkillConcept(
        "Data visualisation",
        ("Data Visualization", "Data visualisation", "Visualization software", "Visualisation software"),
        ("Tableau", "Power BI", "Looker", "Looker Studio", "Google Data Studio", "Qlik", "QlikView", "Qlik Sense", "Matplotlib", "Seaborn", "Plotly", "ggplot"),
    ),
    SkillConcept(
        "Business intelligence",
        ("Business Intelligence", "Business intelligence analysis"),
        ("Power BI", "Tableau", "Qlik", "QlikView", "Qlik Sense", "Looker", "SSRS", "SSAS", "Cognos", "MicroStrategy", "data warehouse", "OLAP"),
    ),
    SkillConcept(
        "Big data",
        ("Big Data",),
        ("Hadoop", "Apache Spark", "PySpark", "Spark SQL", "Apache Hive", "Apache Kafka", "Kafka", "HDFS", "Databricks", "Apache Flink", "MapReduce", "BigQuery", "Snowflake"),
    ),
    SkillConcept(
        "Data warehousing",
        ("Data Warehousing", "data warehouse"),
        ("Snowflake", "Amazon Redshift", "Redshift", "BigQuery", "Azure Synapse", "SSIS", "Informatica", "Talend", "ETL", "star schema", "data warehouse"),
    ),
    SkillConcept(
        "Data cleaning",
        ("Data Cleaning", "data cleansing"),
        ("OpenRefine", "data preprocessing", "data wrangling", "data cleansing", "data cleaning"),
        (_PANDAS,),
    ),
    SkillConcept(
        "Data mining",
        ("Data Mining",),
        ("Weka", "RapidMiner", "KNIME", "text mining", "web scraping", "association rule mining", "k-means", "machine learning"),
    ),
    SkillConcept(
        "Statistics",
        ("Statistics", "statistical"),
        ("SPSS", "Stata", "statistical analysis", "statistical modelling", "statistical modeling", "regression analysis", "hypothesis testing", "R programming", "RStudio"),
    ),
    SkillConcept(
        "Algorithm development",
        ("Algorithm Development",),
        ("data structures and algorithms", "data structures", "algorithm design", "dynamic programming", "graph algorithms", "LeetCode", "HackerRank", "Codeforces", "competitive programming"),
    ),
    # Cloud, DevOps and infrastructure
    SkillConcept(
        "Cloud computing",
        ("Cloud Computing", "Cloud platforms", "Cloud platform", "cloud-based solutions", "Cloud computing platforms"),
        (
            "AWS",
            "Amazon Web Services",
            "Azure",
            "Microsoft Azure",
            "GCP",
            "Google Cloud",
            "Google Cloud Platform",
            "Firebase",
            "Heroku",
            "DigitalOcean",
            "Oracle Cloud",
            "IBM Cloud",
            "Alibaba Cloud",
            "Huawei Cloud",
            "Vercel",
            "Netlify",
            "Cloudflare",
        ),
    ),
    SkillConcept(
        "Cloud architecture",
        ("Cloud Solution Architecture", "Cloud Infrastructure Design", "Cloud Solution Design", "designing cloud solutions"),
        (
            "Terraform",
            "AWS CloudFormation",
            "CloudFormation",
            "infrastructure as code",
            "AWS Solutions Architect",
            "Azure Solutions Architect",
            "solutions architect",
            "cloud architecture",
            "VPC",
            "load balancing",
            "load balancer",
            "auto scaling",
            "Kubernetes",
        ),
    ),
    SkillConcept("CI/CD", ("CI/CD tools", "CI/CD", "continuous integration"), _CI_CD_TOOLS + ("CI/CD pipeline", "CI/CD pipelines")),
    SkillConcept(
        "DevOps",
        ("DevOps practices", "DevOps"),
        _CI_CD_TOOLS + ("Docker", "Kubernetes", "Terraform", "Ansible", "infrastructure as code", "Prometheus", "Grafana", "site reliability engineering"),
    ),
    SkillConcept(
        "Automation",
        ("Automation Skills", "Software automation"),
        ("Bash scripting", "shell scripting", "PowerShell", "Ansible", "Python scripting", "UiPath", "Power Automate", "robotic process automation", "Terraform", "cron jobs", "Zapier"),
        (_SELENIUM,),
    ),
    SkillConcept(
        "Monitoring",
        (
            "Network monitoring tools",
            "Network monitoring",
            "System monitoring",
            "Network infrastructure monitoring",
            "System performance monitoring",
            "Computer system performance monitoring",
            "Internet performance monitoring",
            "=Monitoring",
        ),
        (
            "Wireshark",
            "Nagios",
            "Zabbix",
            "PRTG",
            "SolarWinds",
            "Datadog",
            "Prometheus",
            "Grafana",
            "New Relic",
            "Splunk",
            "ELK stack",
            "Kibana",
            "LibreNMS",
            "SNMP",
            "NetFlow",
            "Dynatrace",
            "AppDynamics",
            "CloudWatch",
            "Azure Monitor",
        ),
    ),
    SkillConcept(
        "Backup and disaster recovery",
        ("Backup and disaster recovery tools", "Backup and disaster recovery", "Data backup and disaster recovery", "Disaster Recovery Planning", "Data backup handling"),
        ("Veeam", "Acronis", "Backup Exec", "Commvault", "Windows Server Backup", "AWS Backup", "Bacula", "backup and recovery", "backup and restore", "disaster recovery plan"),
    ),
    SkillConcept(
        "System administration",
        ("System Administration", "Systems Administration", "Operating system support", "Operating system installation", "Server and IP component management"),
        (
            "Windows Server",
            "Linux administration",
            "Linux server",
            "Linux servers",
            "Active Directory",
            "Ubuntu",
            "CentOS",
            "Red Hat",
            "RHEL",
            "Debian",
            "PowerShell",
            "VMware",
            "VMware vSphere",
            "Hyper-V",
            "VirtualBox",
            "Proxmox",
            "Microsoft Exchange",
            "SCCM",
            "Intune",
        ),
    ),
    SkillConcept(
        "Network administration",
        (
            "Network Administration",
            "Cisco Routing",
            "Network Infrastructure",
            "Network troubleshooting",
            "Router installation",
            "LAN/WAN installation",
            "Network hardware installation",
            "Network performance optimization",
            "Network availability support",
        ),
        (
            "Cisco",
            "CCNA",
            "CCNP",
            "Cisco IOS",
            "Juniper Networks",
            "MikroTik",
            "Packet Tracer",
            "OSPF",
            "EIGRP",
            "BGP",
            "VLAN",
            "VLANs",
            "routing and switching",
            "TCP/IP",
            "DHCP",
            "subnetting",
            "Cisco Meraki",
            "Ubiquiti",
        ),
    ),
    # Cybersecurity
    SkillConcept(
        "Security testing",
        ("Penetration Testing", "Vulnerability Assessment", "Security Assessment", "Cybersecurity Assessment"),
        (
            "Metasploit",
            "Burp Suite",
            "Nmap",
            "Nessus",
            "OpenVAS",
            "OWASP ZAP",
            "OWASP",
            "Kali Linux",
            "Nikto",
            "sqlmap",
            "John the Ripper",
            "Hashcat",
            "ethical hacking",
            "CEH",
            "OSCP",
            "pentest",
            "pentesting",
            "pen testing",
            "vulnerability scanning",
            "Qualys",
            "Acunetix",
            "Nexpose",
            "bug bounty",
            "capture the flag",
            "security audit",
            "security audits",
        ),
    ),
    SkillConcept(
        "Threat detection and incident response",
        ("Intrusion Detection", "Security Incident Response", "Threat Analysis", "threat intelligence"),
        (
            "Snort",
            "Suricata",
            "Zeek",
            "OSSEC",
            "Wazuh",
            "SIEM",
            "Splunk",
            "QRadar",
            "ArcSight",
            "Microsoft Sentinel",
            "Security Onion",
            "IDS/IPS",
            "intrusion detection system",
            "EDR",
            "CrowdStrike",
            "SentinelOne",
            "threat hunting",
            "MITRE ATT&CK",
            "threat intelligence",
        ),
    ),
    SkillConcept(
        "Malware analysis",
        ("Malware Analysis",),
        ("IDA Pro", "Ghidra", "OllyDbg", "Cuckoo Sandbox", "VirusTotal", "YARA rules", "malware sandbox"),
    ),
    SkillConcept(
        "Digital forensics",
        ("Computer Forensics", "Digital Forensics", "Digital evidence investigation", "Digital Evidence Analysis", "Forensic Investigation"),
        ("EnCase", "FTK", "Forensic Toolkit", "Volatility Framework", "Sleuth Kit", "Cellebrite", "X-Ways", "Magnet AXIOM", "disk imaging", "memory forensics", "CHFI"),
    ),
    SkillConcept(
        "Access control",
        ("Access Control", "identity management"),
        (
            "Active Directory",
            "LDAP",
            "AWS IAM",
            "identity and access management",
            "Okta",
            "role-based access control",
            "RBAC",
            "multi-factor authentication",
            "OAuth",
            "single sign-on",
            "SSO",
            "Kerberos",
            "Azure AD",
            "Entra ID",
        ),
    ),
    SkillConcept(
        "Network security",
        ("Network Security",),
        ("firewall", "firewalls", "Palo Alto Networks", "Fortinet", "FortiGate", "Cisco ASA", "pfSense", "VPN", "IPsec", "IDS/IPS", "Snort", "Suricata", "network segmentation"),
    ),
    SkillConcept(
        "Data protection compliance",
        ("Personal Data Protection", "Data Protection Compliance", "Security Standards Compliance", "Data Security", "Data Management Protection", "data protection"),
        ("PDPA", "GDPR", "NIST", "PCI DSS", "PCI-DSS", "HIPAA", "data loss prevention", "DLP", "encryption", "data masking"),
        (_ISO_27001,),
    ),
    # Software engineering
    SkillConcept(
        "Development environments",
        ("Development Environment Software",),
        (
            "Visual Studio Code",
            "VS Code",
            "VSCode",
            "Visual Studio",
            "IntelliJ",
            "IntelliJ IDEA",
            "Eclipse",
            "PyCharm",
            "Android Studio",
            "Xcode",
            "NetBeans",
            "Jupyter Notebook",
            "Jupyter",
            "Sublime Text",
            "WebStorm",
            "Spyder",
            "RStudio",
        ),
    ),
    SkillConcept("Front-end development", ("Front-end development", "Front-end"), _FRONT_END, _FRONT_END_PATTERNS),
    SkillConcept(
        "Back-end development",
        ("Back-end development", "Back-end"),
        (
            "Django",
            "FastAPI",
            "Spring Boot",
            "Laravel",
            "ASP.NET",
            "Ruby on Rails",
            "PHP",
            "REST API",
            "REST APIs",
            "GraphQL",
            "NestJS",
            "microservices",
        ),
        (_NODE, _EXPRESS, _FLASK, _HIBERNATE, _RESTFUL),
    ),
    SkillConcept(
        "Web design",
        ("Web Design",),
        ("HTML", "CSS", "WordPress", "Webflow", "Wix", "Squarespace", "Elementor", "Tailwind CSS") + _DESIGN_TOOLS,
        (_BOOTSTRAP,),
    ),
    SkillConcept(
        "Website management",
        ("Website Management",),
        ("WordPress", "cPanel", "Google Search Console", "content management system", "Joomla", "Drupal", "Shopify"),
    ),
    SkillConcept(
        "Responsive design",
        ("Responsive design", "application responsiveness"),
        ("responsive web design", "responsive design", "mobile-first", "media queries", "Flexbox", "CSS Grid", "Tailwind CSS"),
        (_BOOTSTRAP,),
    ),
    SkillConcept(
        "Mobile development",
        ("cross-platform optimization for mobile", "mobile application", "mobile applications"),
        ("Flutter", "React Native", "Kotlin", "SwiftUI", "Xamarin", "Android Studio", "Jetpack Compose"),
        (_SWIFT,),
    ),
    SkillConcept(
        "APIs and integration",
        ("APIs", "=API", "integrations", "web services", "system integration"),
        ("REST API", "REST APIs", "GraphQL", "gRPC", "Swagger", "OpenAPI", "web services", "API integration", "FastAPI", "webhooks"),
        (_RESTFUL,),
    ),
    SkillConcept(
        "Microservices",
        ("microservices",),
        ("Docker", "Kubernetes", "Spring Cloud", "service mesh", "Istio", "gRPC", "Apache Kafka", "RabbitMQ", "Docker Compose"),
    ),
    SkillConcept(
        "Software design",
        ("System Design", "Software design", "Software architecture design", "Software modeling", "Software modelling"),
        (
            "UML",
            "class diagram",
            "class diagrams",
            "sequence diagram",
            "sequence diagrams",
            "use case diagram",
            "use case diagrams",
            "entity relationship diagram",
            "ERD",
            "design patterns",
            "system architecture",
            "data flow diagram",
            "DFD",
            "MVC",
            "microservices",
        ),
    ),
    # Using a database product proves the product, not administration or
    # design work, so those two concepts need evidence of the activity itself.
    SkillConcept(
        "Database administration",
        ("Database Administration", "Database Management", "Database maintenance", "Database troubleshooting"),
        _DATABASE_ADMINISTRATION,
    ),
    SkillConcept(
        "Database design",
        ("Database Design", "Database Management"),
        _DATABASE_DESIGN,
    ),
    SkillConcept("Relational databases", ("Relational Database Management System",), _RELATIONAL_DATABASES),
    SkillConcept("SQL", ("=SQL",), ("SQL Server", "SQLite", "MariaDB", "T-SQL", "PL/SQL", "BigQuery")),
    SkillConcept(
        "Software testing",
        (
            "Software Testing",
            "Testing Skills",
            "Program testing",
            "System testing",
            "Systems Testing",
            "Quality Assurance",
            "Test case development",
            "Browser and device compatibility testing",
        ),
        _TESTING_TOOLS,
        (_SELENIUM, _JEST),
    ),
    SkillConcept(
        "Defect tracking",
        ("Bug tracking", "Defect tracking database", "Defect documentation"),
        ("Jira", "Bugzilla", "Azure Boards", "Azure DevOps", "MantisBT", "Redmine", "YouTrack", "GitHub Issues", "TestRail", "bug reports", "defect reports"),
    ),
    SkillConcept(
        "Agile methods",
        ("Agile methodology", "Agile Methodologies"),
        ("sprint planning", "sprint backlog", "user stories", "Scrum Master", "Jira"),
        (_SCRUM,),
    ),
    # IT support
    SkillConcept(
        "Technical support",
        (
            "Technical support",
            "Customer technical support",
            "Advanced technical support",
            "Help desk coordination",
            "Hardware and software support",
            "Software and hardware support",
            "Computer hardware support",
        ),
        ("desktop support", "service desk", "ServiceNow", "TeamViewer", "AnyDesk", "CompTIA A+", "ITIL"),
        (_IT_SUPPORT,),
    ),
    SkillConcept(
        "IT service management",
        ("IT service management", "IT operations management"),
        ("ITIL", "ServiceNow", "service desk", "Jira Service Management", "BMC Remedy"),
    ),
    SkillConcept(
        "Hardware troubleshooting",
        ("Hardware troubleshooting", "Computer hardware installation", "Computer repair", "Hardware maintenance", "Hardware setup", "Hardware and software installation"),
        ("CompTIA A+", "PC assembly", "computer assembly", "hardware repair", "laptop repair", "desktop support", "BIOS", "motherboard"),
    ),
    # Design, media and games
    SkillConcept(
        "UI/UX design",
        ("User Interface Design", "User Experience Design", "Design user interactions on web pages", "User Flows"),
        _DESIGN_TOOLS + ("user flows", "user journey", "user journeys", "wireframes", "wireframing", "usability testing", "user research", "user personas", "design system"),
    ),
    SkillConcept(
        "Wireframing and prototyping",
        ("Wireframing", "Prototyping", "Design and prototyping tools", "Web and mobile design tools"),
        _DESIGN_TOOLS + ("wireframes", "mockups", "mock-ups", "low-fidelity prototype", "high-fidelity prototype"),
    ),
    SkillConcept(
        "Usability testing",
        ("Usability Testing", "User Research"),
        ("usability testing", "user testing", "A/B testing", "user interviews", "Hotjar", "card sorting", "heuristic evaluation", "System Usability Scale"),
    ),
    SkillConcept(
        "Graphic design",
        ("Graphic Design", "Graphic design software", "Digital content creation tools", "Digital Content Creation", "2D Software", "Visual Design"),
        (
            "Adobe Photoshop",
            "Photoshop",
            "Adobe Illustrator",
            "Adobe InDesign",
            "InDesign",
            "CorelDRAW",
            "Canva",
            "GIMP",
            "Inkscape",
            "Affinity Designer",
            "Adobe Creative Suite",
            "Adobe Creative Cloud",
        ),
    ),
    SkillConcept(
        "Video editing",
        ("Video Editing",),
        ("Adobe Premiere Pro", "Premiere Pro", "Final Cut Pro", "DaVinci Resolve", "CapCut", "Adobe After Effects", "After Effects", "Vegas Pro", "Filmora"),
    ),
    SkillConcept(
        "Animation",
        ("Motion Graphic", "Animation", "Computer Animation", "2D and 3D animation software", "3D Animation Modeling and Rigging"),
        ("Adobe After Effects", "After Effects", "Adobe Animate", "Toon Boom", "Autodesk Maya", "Cinema 4D", "Moho"),
        (_BLENDER,),
    ),
    SkillConcept(
        "3D modelling",
        ("3D Modelling", "3D modelling software", "3D art asset creation", "3D Lighting and Rendering"),
        ("Autodesk Maya", "ZBrush", "Substance Painter", "SketchUp", "Houdini", "Cinema 4D"),
        (_BLENDER,),
    ),
    SkillConcept(
        "Game development",
        ("Game engines", "Game Development", "Mobile Games"),
        ("Unreal Engine", "Godot", "GameMaker", "GameMaker Studio", "game development"),
        (_UNITY,),
    ),
    # Specific products named by the catalogue. The resume often uses a
    # shorter name or a framework that can only be used with the product.
    SkillConcept("Amazon Web Services", ("Amazon Web Services",), ("AWS",)),
    SkillConcept("Microsoft Azure", ("Microsoft Azure",), ("Azure",)),
    SkillConcept("Google Cloud Platform", ("Google Cloud Platform",), ("GCP", "Google Cloud")),
    SkillConcept("Adobe Photoshop", ("Adobe Photoshop",), ("Photoshop",)),
    SkillConcept("Adobe Illustrator", ("Adobe Illustrator",), (), (("Illustrator", r"\bIllustrator\b"),)),
    SkillConcept("Apache Tomcat", ("Apache Tomcat",), ("Tomcat",)),
    SkillConcept("MongoDB", ("Mongo DB",), ("MongoDB", "MongoDB Atlas", "Mongoose")),
    SkillConcept("Oracle Database", ("Oracle Database",), ("Oracle DB", "Oracle SQL", "PL/SQL")),
    SkillConcept(".NET", ("=.NET",), ("ASP.NET", "C#", "Entity Framework", "Blazor", "VB.NET")),
    SkillConcept("Python", ("=Python",), ("Django", "FastAPI", "NumPy", "PyTorch", "scikit-learn", "PySpark", "Jupyter"), (_FLASK, _PANDAS)),
    SkillConcept("Java", ("=Java",), ("Spring Boot", "Spring Framework", "JSP", "Gradle", "J2EE", "Jakarta EE"), (_HIBERNATE,)),
    SkillConcept("PHP", ("=PHP",), ("Laravel", "CodeIgniter", "Symfony")),
    SkillConcept("CSS", ("=CSS",), ("Tailwind CSS", "Sass", "SCSS"), (_BOOTSTRAP,)),
)
