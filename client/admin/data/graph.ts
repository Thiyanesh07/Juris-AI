export type GraphEntityType =
  | 'ARTICLE'
  | 'ACT'
  | 'SECTION'
  | 'AMENDMENT'
  | 'RULE'
  | 'REGULATION'
  | 'JUDGMENT'
  | 'COURT';

export type GraphRelationType =
  | 'BELONGS_TO'
  | 'CONTAINS'
  | 'DEFINES'
  | 'AMENDS'
  | 'MODIFIES'
  | 'INTERPRETS'
  | 'REFERENCES'
  | 'OVERRULES'
  | 'CONFLICTS_WITH';

export interface GraphNodeData {
  id: string;
  label: string;
  type: GraphEntityType;
  x: number;
  y: number;
  description: string;
  identifier: string;
  sourceDocId?: string;
  jurisdiction?: string;
}

export interface GraphEdgeData {
  id: string;
  source: string;
  target: string;
  relationship: GraphRelationType;
  description?: string;
}

export const INITIAL_GRAPH_NODES: GraphNodeData[] = [
  // Constitution & Articles
  {
    id: 'n_const',
    label: 'Constitution of India',
    type: 'ACT',
    x: 480,
    y: 200,
    identifier: 'Const. India (1950)',
    description: 'Supreme law of the Republic of India defining fundamental rights & framework.',
    sourceDocId: 'doc_101',
    jurisdiction: 'Union of India',
  },
  {
    id: 'n_art21',
    label: 'Article 21 - Life & Liberty',
    type: 'ARTICLE',
    x: 320,
    y: 260,
    identifier: 'Art. 21 Const.',
    description: 'Protection of life and personal liberty except according to procedure established by law.',
    jurisdiction: 'Union of India',
  },
  {
    id: 'n_art14',
    label: 'Article 14 - Equality Before Law',
    type: 'ARTICLE',
    x: 480,
    y: 330,
    identifier: 'Art. 14 Const.',
    description: 'State shall not deny to any person equality before the law or equal protection of laws.',
    jurisdiction: 'Union of India',
  },
  {
    id: 'n_art19',
    label: 'Article 19 - Fundamental Freedoms',
    type: 'ARTICLE',
    x: 640,
    y: 260,
    identifier: 'Art. 19 Const.',
    description: 'Protection of certain rights regarding freedom of speech, assembly, association.',
    jurisdiction: 'Union of India',
  },
  {
    id: 'n_art32',
    label: 'Article 32 - Constitutional Remedies',
    type: 'ARTICLE',
    x: 220,
    y: 180,
    identifier: 'Art. 32 Const.',
    description: 'Right to move Supreme Court by appropriate proceedings for enforcement of rights.',
    jurisdiction: 'Union of India',
  },

  // Amendments
  {
    id: 'n_amend44',
    label: '44th Amendment Act, 1978',
    type: 'AMENDMENT',
    x: 160,
    y: 320,
    identifier: '44th Amend. Act',
    description: 'Safeguarded Article 21 from suspension during Emergency declaration.',
    jurisdiction: 'Union of India',
  },
  {
    id: 'n_amend86',
    label: '86th Amendment Act, 2002',
    type: 'AMENDMENT',
    x: 280,
    y: 390,
    identifier: '86th Amend. Act',
    description: 'Inserted Article 21A establishing Right to Education as a fundamental right.',
    jurisdiction: 'Union of India',
  },

  // Acts & Sections
  {
    id: 'n_ipc',
    label: 'Indian Penal Code, 1860',
    type: 'ACT',
    x: 480,
    y: 480,
    identifier: 'IPC (Act 45 of 1860)',
    description: 'Official criminal code of India covering penal offenses.',
    sourceDocId: 'doc_102',
    jurisdiction: 'Union of India',
  },
  {
    id: 'n_bns',
    label: 'Bharatiya Nyaya Sanhita, 2023',
    type: 'ACT',
    x: 660,
    y: 480,
    identifier: 'BNS (Act 45 of 2023)',
    description: 'Modernized penal statute replacing the Indian Penal Code 1860.',
    sourceDocId: 'doc_103',
    jurisdiction: 'Union of India',
  },
  {
    id: 'n_sec302',
    label: 'Section 302 IPC - Murder Penalty',
    type: 'SECTION',
    x: 360,
    y: 540,
    identifier: 'Sec. 302 IPC',
    description: 'Prescribes punishment for murder under Indian Penal Code.',
    jurisdiction: 'Union of India',
  },
  {
    id: 'n_sec101',
    label: 'Section 101 BNS - Murder Provision',
    type: 'SECTION',
    x: 580,
    y: 560,
    identifier: 'Sec. 101 BNS',
    description: 'Modernized penal provision for murder corresponding to Section 302 IPC.',
    jurisdiction: 'Union of India',
  },
  {
    id: 'n_crpc',
    label: 'Code of Criminal Procedure, 1973',
    type: 'ACT',
    x: 200,
    y: 480,
    identifier: 'CrPC (Act 2 of 1974)',
    description: 'Procedural legislation for administration of criminal law in India.',
    sourceDocId: 'doc_104',
    jurisdiction: 'Union of India',
  },
  {
    id: 'n_sec438',
    label: 'Section 438 CrPC - Anticipatory Bail',
    type: 'SECTION',
    x: 100,
    y: 550,
    identifier: 'Sec. 438 CrPC',
    description: 'Direction for grant of bail to person apprehending arrest.',
    jurisdiction: 'Union of India',
  },
  {
    id: 'n_itact',
    label: 'Information Technology Act, 2000',
    type: 'ACT',
    x: 820,
    y: 330,
    identifier: 'IT Act, 2000',
    description: 'Primary law dealing with cybercrime and electronic commerce in India.',
    sourceDocId: 'doc_106',
    jurisdiction: 'Union of India',
  },
  {
    id: 'n_sec66a',
    label: 'Section 66A IT Act - Speech Penalty',
    type: 'SECTION',
    x: 760,
    y: 230,
    identifier: 'Sec. 66A IT Act',
    description: 'Struck down provision penalizing offensive messages sent via communication services.',
    jurisdiction: 'Union of India',
  },

  // Judgments & Courts
  {
    id: 'n_sc',
    label: 'Supreme Court of India',
    type: 'COURT',
    x: 480,
    y: 60,
    identifier: 'Apex Court India',
    description: 'Highest judicial forum and final court of appeal under the Constitution.',
    jurisdiction: 'Union of India',
  },
  {
    id: 'n_j_kesavananda',
    label: 'Kesavananda Bharati v. Kerala (1973)',
    type: 'JUDGMENT',
    x: 300,
    y: 100,
    identifier: '1973 4 SCC 225',
    description: 'Landmark ruling establishing the Basic Structure Doctrine of the Constitution.',
    sourceDocId: 'doc_107',
    jurisdiction: 'Supreme Court of India',
  },
  {
    id: 'n_j_maneka',
    label: 'Maneka Gandhi v. Union of India (1978)',
    type: 'JUDGMENT',
    x: 660,
    y: 120,
    identifier: '1978 1 SCC 248',
    description: 'Expanded Article 21 to mandate due procedure must be fair, just, and reasonable.',
    sourceDocId: 'doc_108',
    jurisdiction: 'Supreme Court of India',
  },
  {
    id: 'n_j_shreya',
    label: 'Shreya Singhal v. Union of India (2015)',
    type: 'JUDGMENT',
    x: 840,
    y: 150,
    identifier: '2015 5 SCC 1',
    description: 'Struck down Section 66A IT Act as unconstitutional for violating free speech under Art. 19(1)(a).',
    jurisdiction: 'Supreme Court of India',
  },
];

export const INITIAL_GRAPH_EDGES: GraphEdgeData[] = [
  // Constitutional Belongs_To Edges
  { id: 'e1', source: 'n_art21', target: 'n_const', relationship: 'BELONGS_TO' },
  { id: 'e2', source: 'n_art14', target: 'n_const', relationship: 'BELONGS_TO' },
  { id: 'e3', source: 'n_art19', target: 'n_const', relationship: 'BELONGS_TO' },
  { id: 'e4', source: 'n_art32', target: 'n_const', relationship: 'BELONGS_TO' },

  // Amendments -> Articles
  { id: 'e5', source: 'n_amend44', target: 'n_art21', relationship: 'AMENDS', description: 'Restricted suspension during Emergency' },
  { id: 'e6', source: 'n_amend86', target: 'n_art21', relationship: 'AMENDS', description: 'Inserted Art 21A Right to Education' },

  // Acts & Sections Belongs_To / Contains
  { id: 'e7', source: 'n_sec302', target: 'n_ipc', relationship: 'BELONGS_TO' },
  { id: 'e8', source: 'n_bns', target: 'n_ipc', relationship: 'MODIFIES', description: 'Replaces IPC 1860' },
  { id: 'e9', source: 'n_sec101', target: 'n_bns', relationship: 'BELONGS_TO' },
  { id: 'e10', source: 'n_sec101', target: 'n_sec302', relationship: 'MODIFIES', description: 'Substitutes murder penalty provision' },
  { id: 'e11', source: 'n_sec438', target: 'n_crpc', relationship: 'BELONGS_TO' },
  { id: 'e12', source: 'n_sec66a', target: 'n_itact', relationship: 'BELONGS_TO' },

  // Judgments -> Interpretation / References / Overrules
  { id: 'e13', source: 'n_j_kesavananda', target: 'n_const', relationship: 'INTERPRETS', description: 'Establishes Basic Structure Doctrine' },
  { id: 'e14', source: 'n_j_kesavananda', target: 'n_art32', relationship: 'REFERENCES' },
  { id: 'e15', source: 'n_j_maneka', target: 'n_art21', relationship: 'INTERPRETS', description: 'Expanded due process & personal liberty' },
  { id: 'e16', source: 'n_j_maneka', target: 'n_art14', relationship: 'INTERPRETS', description: 'Rule against arbitrariness' },
  { id: 'e17', source: 'n_j_maneka', target: 'n_sec438', relationship: 'REFERENCES' },
  { id: 'e18', source: 'n_j_shreya', target: 'n_sec66a', relationship: 'OVERRULES', description: 'Struck down Sec 66A IT Act' },
  { id: 'e19', source: 'n_j_shreya', target: 'n_art19', relationship: 'INTERPRETS', description: 'Upheld online free speech' },
  { id: 'e20', source: 'n_sec66a', target: 'n_art19', relationship: 'CONFLICTS_WITH', description: 'Violated freedom of speech' },

  // Court -> Judgments
  { id: 'e21', source: 'n_sc', target: 'n_j_kesavananda', relationship: 'CONTAINS' },
  { id: 'e22', source: 'n_sc', target: 'n_j_maneka', relationship: 'CONTAINS' },
  { id: 'e23', source: 'n_sc', target: 'n_j_shreya', relationship: 'CONTAINS' },
];
