import {
  ResearchResult,
  EvidenceItem,
  Citation,
  ReasoningStep,
  GraphNode,
  GraphEdge,
  TimelineEvent,
  ResearchHistoryRecord,
  SavedResearch,
  UserProfile,
  ResearchSession,
} from '@/lib/types';

// ============================================================
// MOCK USER PROFILE
// ============================================================
export const MOCK_USER_PROFILE: UserProfile = {
  id: 'usr_researcher_001',
  name: 'Adv. Priya Nair',
  email: 'priya.nair@chambers.in',
  role: 'Senior Legal Researcher',
  organization: 'Nair & Associates, Supreme Court',
  preferredMode: 'COMPREHENSIVE',
  language: 'English (India)',
  timezone: 'Asia/Kolkata',
  avatarUrl: undefined,
  notificationsEnabled: true,
  joinedAt: '2026-06-15T00:00:00Z',
};

// ============================================================
// MOCK RESEARCH RESULT: Article 21 Query
// ============================================================
export const MOCK_RESEARCH_RESULT_ART21: ResearchResult = {
  answer:
    'Article 21 of the Constitution of India, guaranteeing the right to life and personal liberty, has undergone a profound judicial expansion since the landmark Maneka Gandhi judgment (1978). The Supreme Court has interpreted it to encompass procedural due process, right to livelihood, right to education, environmental rights, and the right to a speedy trial through successive multi-hop reasoning across constitutional provisions and judicial precedents.',

  insufficientEvidence: false,
  status: 'answered',
  graphAvailable: true,
  reasoningAvailable: true,
  timelineAvailable: true,

  summary:
    'Article 21 of the Constitution of India, guaranteeing the right to life and personal liberty, has undergone a profound judicial expansion since the landmark Maneka Gandhi judgment (1978). The Supreme Court has interpreted it to encompass procedural due process, right to livelihood, right to education, environmental rights, and the right to a speedy trial through successive multi-hop reasoning across constitutional provisions and judicial precedents.',

  legalFramework:
    'Article 21 reads: "No person shall be deprived of his life or personal liberty except according to procedure established by law." Initially interpreted narrowly in A.K. Gopalan v. State of Madras (1950), the Supreme Court held that "procedure established by law" simply meant any law enacted by a competent legislature, irrespective of its fairness. This was the dominant position for nearly three decades.',

  judicialInterpretation:
    'In Maneka Gandhi v. Union of India (1978) [1], a seven-judge Constitution Bench fundamentally altered this position. Justice P.N. Bhagwati held that Article 21 must be read conjunctively with Articles 14 and 19. The "procedure established by law" must be reasonable, fair, and just — not arbitrary or oppressive. This reading imported substantive due process into Article 21 for the first time in Indian constitutional jurisprudence. [2]\n\nFrancis Coralie Mullin v. Union Territory of Delhi (1981) [3] extended Article 21 to encompass the right to live with basic human dignity, including access to nutrition, clothing, shelter, and education. Justice Bhagwati articulated that "the right to live is not restricted to mere animal existence."\n\nFollowing Maneka Gandhi, the Supreme Court used Article 21 as a constitutional anchor for a series of socio-economic rights. In Olga Tellis v. Bombay Municipal Corporation (1985) [4], the Court held that the right to livelihood is an integral component of Article 21. Pavement dwellers could not be evicted without a fair hearing.',

  developmentOverTime:
    'The 1978 Maneka Gandhi decision triggered a cascading line of precedents interpreting Article 21 expansively. The Court progressively recognized: right to legal aid (Hussainara Khatoon v. State of Bihar, 1979) [5]; right to speedy trial; right to privacy; environmental rights (MC Mehta v. Union of India, 1987); right to health; right to education (later codified in Article 21-A by the 86th Constitutional Amendment, 2002); and right to clean drinking water. Each judicial interpretation built upon prior ones through multi-hop reasoning across constitutional provisions and judicial authorities.',

  reasoning:
    'GraphRAG traversal identified Article 21 as the seed entity. Multi-hop traversal across the Constitutional Law subgraph identified Maneka Gandhi v. UOI as the key interpretive authority via the INTERPRETS edge. The 44th Amendment relationship via the AMENDS edge confirmed the emergency-period protection. Subsequent case law authorities were linked through REFERENCES and OVERRULES relationships. Evidence was fused from VECTOR and GRAPH retrieval, with HYBRID scoring prioritising semantically relevant passages from the retrieved judgment texts.',

  conclusion:
    'Article 21 today represents one of the most expansive fundamental rights in comparative constitutional law. Through sustained judicial interpretation across five decades, the Supreme Court has transformed a relatively brief constitutional guarantee into a comprehensive charter of civil, political and socio-economic rights. The multi-hop reasoning graph demonstrates that no individual judgment operates in isolation — each builds upon, references, and extends prior constitutional understanding through a web of inter-connected legal relationships.',

  disclaimer:
    'Research aid only. Verify cited authorities and consult the underlying judgments and legislation before relying on this analysis. This is demo data generated by a prototype research pipeline — not live retrieval from a verified legal database.',

  evidence: [
    {
      id: 'ev_001',
      entityName: 'Article 21',
      entityType: 'ARTICLE',
      sourceDocumentTitle: 'Constitution of India',
      sourceDocumentType: 'CONSTITUTION',
      provision: 'Part III, Article 21',
      relevanceScore: 0.98,
      excerpt:
        'No person shall be deprived of his life or personal liberty except according to procedure established by law.',
      retrievalSource: 'HYBRID',
      year: 1950,
    },
    {
      id: 'ev_002',
      entityName: 'Maneka Gandhi v. Union of India',
      entityType: 'JUDGMENT',
      sourceDocumentTitle: 'Maneka Gandhi v. Union of India (1978)',
      sourceDocumentType: 'JUDGMENT',
      provision: 'AIR 1978 SC 597; 1978 1 SCC 248',
      relevanceScore: 0.96,
      excerpt:
        'Procedure established by law under Article 21 must answer the test of reasonableness in order to be in conformity with Article 14.',
      retrievalSource: 'HYBRID',
      year: 1978,
    },
    {
      id: 'ev_003',
      entityName: 'Article 14',
      entityType: 'ARTICLE',
      sourceDocumentTitle: 'Constitution of India',
      sourceDocumentType: 'CONSTITUTION',
      provision: 'Part III, Article 14',
      relevanceScore: 0.87,
      excerpt:
        'The State shall not deny to any person equality before the law or the equal protection of the laws within the territory of India.',
      retrievalSource: 'GRAPH',
      year: 1950,
    },
    {
      id: 'ev_004',
      entityName: 'Olga Tellis v. Bombay Municipal Corporation',
      entityType: 'JUDGMENT',
      sourceDocumentTitle: 'Olga Tellis v. BMC (1985)',
      sourceDocumentType: 'JUDGMENT',
      provision: 'AIR 1986 SC 180; 1985 3 SCC 545',
      relevanceScore: 0.91,
      excerpt:
        'The sweep of the right to life conferred by Article 21 is wide and far reaching. It does not mean merely that life cannot be extinguished or taken away as, for example, by the imposition and execution of the death sentence.',
      retrievalSource: 'VECTOR',
      year: 1985,
    },
    {
      id: 'ev_005',
      entityName: 'Francis Coralie Mullin v. UT Delhi',
      entityType: 'JUDGMENT',
      sourceDocumentTitle: 'Francis Coralie Mullin v. Union Territory of Delhi (1981)',
      sourceDocumentType: 'JUDGMENT',
      provision: 'AIR 1981 SC 746; 1981 1 SCC 608',
      relevanceScore: 0.89,
      excerpt:
        'The right to live is not restricted to mere animal existence. It means the right to live with human dignity and all that goes along with it.',
      retrievalSource: 'VECTOR',
      year: 1981,
    },
    {
      id: 'ev_006',
      entityName: 'Shreya Singhal v. Union of India',
      entityType: 'JUDGMENT',
      sourceDocumentTitle: 'Shreya Singhal v. Union of India (2015)',
      sourceDocumentType: 'JUDGMENT',
      provision: '2015 5 SCC 1',
      relevanceScore: 0.78,
      excerpt:
        "Freedom of speech and expression includes the right to communicate or circulate one's opinion without interference.",
      retrievalSource: 'GRAPH',
      year: 2015,
    },
  ],

  citations: [
    {
      id: 'cit_001',
      index: 1,
      caseName: 'Maneka Gandhi v. Union of India',
      court: 'Supreme Court of India',
      year: 1978,
      citation: 'AIR 1978 SC 597; 1978 1 SCC 248',
      documentType: 'JUDGMENT',
      provision: 'Article 21 read with Articles 14 and 19',
      sourceDocumentTitle: 'Maneka Gandhi v. Union of India (1978)',
      sourceLocation: 'SCR Judgment Para 14, Page 254',
      excerpt:
        'Procedure established by law under Article 21 must answer the test of reasonableness in order to be in conformity with Article 14.',
      status: 'VERIFIED',
    },
    {
      id: 'cit_002',
      index: 2,
      caseName: 'A.K. Gopalan v. State of Madras',
      court: 'Supreme Court of India',
      year: 1950,
      citation: 'AIR 1950 SC 27; 1950 SCR 88',
      documentType: 'JUDGMENT',
      provision: 'Article 21 — Original Interpretation',
      sourceDocumentTitle: 'A.K. Gopalan v. State of Madras (1950)',
      sourceLocation: 'Judgment Para 7, Majority Opinion',
      excerpt:
        '"Procedure established by law" in Article 21 means procedure prescribed by the law of the State.',
      status: 'VERIFIED',
    },
    {
      id: 'cit_003',
      index: 3,
      caseName: 'Francis Coralie Mullin v. Union Territory of Delhi',
      court: 'Supreme Court of India',
      year: 1981,
      citation: 'AIR 1981 SC 746; 1981 1 SCC 608',
      documentType: 'JUDGMENT',
      provision: 'Article 21 — Right to Live with Dignity',
      sourceDocumentTitle: 'Francis Coralie Mullin v. Union Territory of Delhi (1981)',
      sourceLocation: 'Para 8',
      excerpt: 'The right to live is not restricted to mere animal existence.',
      status: 'VERIFIED',
    },
    {
      id: 'cit_004',
      index: 4,
      caseName: 'Olga Tellis v. Bombay Municipal Corporation',
      court: 'Supreme Court of India',
      year: 1985,
      citation: 'AIR 1986 SC 180; 1985 3 SCC 545',
      documentType: 'JUDGMENT',
      provision: 'Article 21 — Right to Livelihood',
      sourceDocumentTitle: 'Olga Tellis v. BMC (1985)',
      sourceLocation: 'Para 32',
      excerpt:
        'The right to livelihood is an integral component of the right to life guaranteed by Article 21.',
      status: 'VERIFIED',
    },
    {
      id: 'cit_005',
      index: 5,
      caseName: 'Hussainara Khatoon v. State of Bihar',
      court: 'Supreme Court of India',
      year: 1979,
      citation: 'AIR 1979 SC 1360; 1979 3 SCC 532',
      documentType: 'JUDGMENT',
      provision: 'Article 21 — Right to Speedy Trial',
      sourceDocumentTitle: 'Hussainara Khatoon v. State of Bihar (1979)',
      sourceLocation: 'Para 6',
      excerpt:
        'The right to speedy trial is a fundamental right implicit in the guarantee of life and personal liberty enshrined in Article 21.',
      status: 'NEEDS_REVIEW',
    },
  ],

  reasoningSteps: [
    {
      step: 1,
      description: 'Query identified "Article 21", "personal liberty", "Supreme Court", and "interpretation" as legal seed entities.',
    },
    {
      step: 2,
      description: 'VECTOR retrieval returned top-8 semantically similar passages from the constitutional law corpus.',
      entityName: 'Article 21',
    },
    {
      step: 3,
      description: 'GRAPH traversal from Article 21 node identified Maneka Gandhi v. UOI via the INTERPRETS edge (depth 1).',
      entityName: 'Article 21',
      relationLabel: 'INTERPRETS',
      targetEntityName: 'Maneka Gandhi v. UOI (1978)',
    },
    {
      step: 4,
      description: 'Traversal continued to Articles 14 and 19 via the BELONGS_TO and REFERENCES relationships (depth 2).',
      entityName: 'Maneka Gandhi v. UOI (1978)',
      relationLabel: 'REFERENCES',
      targetEntityName: 'Article 14 (Equality Before Law)',
    },
    {
      step: 5,
      description: 'Later judgment authorities (Francis Coralie, Olga Tellis, Hussainara) linked via REFERENCES edges from Maneka Gandhi (depth 2–3).',
      entityName: 'Maneka Gandhi v. UOI (1978)',
      relationLabel: 'REFERENCES',
      targetEntityName: 'Francis Coralie Mullin v. UT Delhi (1981)',
    },
    {
      step: 6,
      description: 'A.K. Gopalan identified via OVERRULES relationship from Maneka Gandhi — confirmed as the earlier, narrower position.',
      entityName: 'Maneka Gandhi v. UOI (1978)',
      relationLabel: 'OVERRULES',
      targetEntityName: 'A.K. Gopalan v. State of Madras (1950)',
    },
    {
      step: 7,
      description: 'Evidence fusion merged VECTOR passages with GRAPH entity evidence weighted at hybrid ratio 0.50. Minimum evidence score threshold 0.70 applied.',
    },
    {
      step: 8,
      description: 'Citation verification completed: 4/5 citations verified against retrieved evidence. 1 citation flagged for secondary source review.',
    },
  ],

  graphNodes: [
    { id: 'n_query', label: 'Research Query', type: 'QUERY', x: 300, y: 40, isQuery: true },
    { id: 'n_art21', label: 'Article 21', type: 'ARTICLE', x: 300, y: 140, isSeed: true },
    { id: 'n_art14', label: 'Article 14', type: 'ARTICLE', x: 140, y: 260 },
    { id: 'n_art19', label: 'Article 19', type: 'ARTICLE', x: 460, y: 260 },
    { id: 'n_maneka', label: 'Maneka Gandhi (1978)', type: 'JUDGMENT', x: 300, y: 280 },
    { id: 'n_gopalan', label: 'A.K. Gopalan (1950)', type: 'JUDGMENT', x: 80, y: 400 },
    { id: 'n_coralie', label: 'Francis Coralie (1981)', type: 'JUDGMENT', x: 220, y: 400 },
    { id: 'n_olga', label: 'Olga Tellis (1985)', type: 'JUDGMENT', x: 380, y: 400 },
    { id: 'n_hussainara', label: 'Hussainara (1979)', type: 'JUDGMENT', x: 520, y: 400 },
  ],

  graphEdges: [
    { id: 'e1', sourceId: 'n_query', targetId: 'n_art21', label: 'SEED_ENTITY' },
    { id: 'e2', sourceId: 'n_maneka', targetId: 'n_art21', label: 'INTERPRETS' },
    { id: 'e3', sourceId: 'n_maneka', targetId: 'n_art14', label: 'REFERENCES' },
    { id: 'e4', sourceId: 'n_maneka', targetId: 'n_art19', label: 'REFERENCES' },
    { id: 'e5', sourceId: 'n_maneka', targetId: 'n_gopalan', label: 'OVERRULES' },
    { id: 'e6', sourceId: 'n_coralie', targetId: 'n_maneka', label: 'REFERENCES' },
    { id: 'e7', sourceId: 'n_olga', targetId: 'n_maneka', label: 'REFERENCES' },
    { id: 'e8', sourceId: 'n_hussainara', targetId: 'n_maneka', label: 'REFERENCES' },
  ],

  timeline: [
    {
      id: 'tl_1',
      year: '1950',
      title: 'A.K. Gopalan v. State of Madras',
      documentType: 'JUDGMENT',
      description: 'Supreme Court holds "procedure established by law" means any law passed by legislature; no substantive due process.',
      importance: 'HIGH',
    },
    {
      id: 'tl_2',
      year: '1950',
      title: 'Constitution of India Enacted',
      documentType: 'CONSTITUTION',
      description: 'Article 21 guarantees right to life and personal liberty against State deprivation without procedure established by law.',
      importance: 'HIGH',
    },
    {
      id: 'tl_3',
      year: '1978',
      title: 'Maneka Gandhi v. Union of India',
      documentType: 'JUDGMENT',
      description: 'Seven-judge bench overrules Gopalan. Article 21 procedure must be reasonable, fair and just. Read conjunctively with Arts 14 & 19.',
      importance: 'HIGH',
    },
    {
      id: 'tl_4',
      year: '1979',
      title: 'Hussainara Khatoon v. State of Bihar',
      documentType: 'JUDGMENT',
      description: 'Right to speedy trial recognized as fundamental right under Article 21.',
      importance: 'MEDIUM',
    },
    {
      id: 'tl_5',
      year: '1981',
      title: 'Francis Coralie Mullin v. UT Delhi',
      documentType: 'JUDGMENT',
      description: 'Article 21 extends to right to live with human dignity, including basic necessities.',
      importance: 'HIGH',
    },
    {
      id: 'tl_6',
      year: '1985',
      title: 'Olga Tellis v. Bombay Municipal Corporation',
      documentType: 'JUDGMENT',
      description: 'Right to livelihood declared integral component of Article 21 right to life.',
      importance: 'HIGH',
    },
    {
      id: 'tl_7',
      year: '2002',
      title: '86th Constitutional Amendment — Article 21A',
      documentType: 'AMENDMENT',
      description: 'Right to free and compulsory education for children aged 6–14 years constitutionally guaranteed as Article 21A.',
      importance: 'HIGH',
    },
  ],

  sourcesCount: 6,
  citationStatus: 'PARTIAL',
};

// ============================================================
// MOCK RESEARCH HISTORY
// ============================================================
export const MOCK_HISTORY_RECORDS: ResearchHistoryRecord[] = [
  {
    id: 'hist_001',
    query: 'How has the interpretation of Article 21 evolved through Supreme Court decisions?',
    mode: 'COMPREHENSIVE',
    createdAt: '2026-09-28T08:30:00Z',
    sourcesCount: 6,
    citationStatus: 'PARTIAL',
    saved: true,
  },
  {
    id: 'hist_002',
    query: 'What are the key differences between the Indian Penal Code 1860 and the Bharatiya Nyaya Sanhita 2023?',
    mode: 'STATUTORY',
    createdAt: '2026-09-27T15:10:00Z',
    sourcesCount: 8,
    citationStatus: 'ALL_VERIFIED',
    saved: false,
  },
  {
    id: 'hist_003',
    query: 'Explain the Basic Structure Doctrine and which constitutional amendments have been struck down under it.',
    mode: 'CONSTITUTIONAL',
    createdAt: '2026-09-26T11:45:00Z',
    sourcesCount: 11,
    citationStatus: 'ALL_VERIFIED',
    saved: true,
  },
  {
    id: 'hist_004',
    query: 'What is anticipatory bail under Section 438 CrPC and how has the Supreme Court interpreted it?',
    mode: 'CASE_LAW',
    createdAt: '2026-09-25T09:30:00Z',
    sourcesCount: 5,
    citationStatus: 'ALL_VERIFIED',
    saved: false,
  },
  {
    id: 'hist_005',
    query: 'What constitutional provisions govern freedom of speech in India and what restrictions are permissible?',
    mode: 'CONSTITUTIONAL',
    createdAt: '2026-09-24T14:00:00Z',
    sourcesCount: 9,
    citationStatus: 'PARTIAL',
    saved: true,
  },
  {
    id: 'hist_006',
    query: 'How does Section 302 BNS 2023 differ from Section 302 IPC in its provisions for murder?',
    mode: 'STATUTORY',
    createdAt: '2026-09-23T10:15:00Z',
    sourcesCount: 4,
    citationStatus: 'ALL_VERIFIED',
    saved: false,
  },
];

// ============================================================
// MOCK SAVED RESEARCH
// ============================================================
export const MOCK_SAVED_RESEARCH: SavedResearch[] = [
  {
    id: 'saved_001',
    title: 'Article 21 — Evolution of Personal Liberty',
    query: 'How has the interpretation of Article 21 evolved through Supreme Court decisions?',
    summary:
      'Comprehensive analysis of how Article 21 expanded from a narrow procedural guarantee in A.K. Gopalan to a substantive due process right encompassing livelihood, dignity, education, and health.',
    mode: 'COMPREHENSIVE',
    savedAt: '2026-09-28T09:00:00Z',
    authorities: ['Maneka Gandhi v. UOI (1978)', 'Olga Tellis v. BMC (1985)', 'Francis Coralie (1981)'],
    tags: ['Article 21', 'Fundamental Rights', 'Due Process', 'Supreme Court'],
  },
  {
    id: 'saved_002',
    title: 'Basic Structure Doctrine — Kesavananda Bharati',
    query: 'Explain the Basic Structure Doctrine and which constitutional amendments have been struck down under it.',
    summary:
      'The Basic Structure Doctrine, established in Kesavananda Bharati v. State of Kerala (1973), holds that Parliament cannot amend the constitution so as to destroy its basic features.',
    mode: 'CONSTITUTIONAL',
    savedAt: '2026-09-26T12:00:00Z',
    authorities: ['Kesavananda Bharati v. State of Kerala (1973)', 'Minerva Mills v. UOI (1980)', 'Indira Gandhi v. Raj Narain (1975)'],
    tags: ['Basic Structure', 'Constitutional Amendments', 'Article 368', 'Parliamentary Sovereignty'],
  },
  {
    id: 'saved_003',
    title: 'Freedom of Speech — Article 19(1)(a)',
    query: 'What constitutional provisions govern freedom of speech in India and what restrictions are permissible?',
    summary:
      'Article 19(1)(a) guarantees freedom of speech and expression, subject to reasonable restrictions under Article 19(2) on grounds of sovereignty, security, public order, decency, and defamation.',
    mode: 'CONSTITUTIONAL',
    savedAt: '2026-09-24T14:30:00Z',
    authorities: ['Shreya Singhal v. UOI (2015)', 'Bennett Coleman v. UOI (1973)', 'S. Rangarajan v. P. Jagjivan Ram (1989)'],
    tags: ['Article 19', 'Freedom of Speech', 'Reasonable Restrictions', 'IT Act'],
  },
];
