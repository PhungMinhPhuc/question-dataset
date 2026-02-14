--
-- PostgreSQL database dump
--

\restrict 8FaRNXGi1Drc4LxOKKhOMalfVjTAlXmgKXbJbdZiTHcUtGDMLgyb4MpS6TsJlHC

-- Dumped from database version 18.3
-- Dumped by pg_dump version 18.3

-- Started on 2026-06-09 16:35:15

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 219 (class 1259 OID 124456)
-- Name: accounts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounts (
    id bigint NOT NULL,
    public_id uuid DEFAULT gen_random_uuid(),
    email character varying NOT NULL,
    password character varying NOT NULL,
    is_active boolean DEFAULT true,
    role character varying NOT NULL,
    name character varying,
    avatar_url character varying,
    create_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT check_valid_role CHECK (((role)::text = ANY (ARRAY[('student'::character varying)::text, ('teacher'::character varying)::text, ('admin'::character varying)::text])))
);


ALTER TABLE public.accounts OWNER TO postgres;

--
-- TOC entry 220 (class 1259 OID 124470)
-- Name: accounts_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.accounts_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.accounts_id_seq OWNER TO postgres;

--
-- TOC entry 5184 (class 0 OID 0)
-- Dependencies: 220
-- Name: accounts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.accounts_id_seq OWNED BY public.accounts.id;


--
-- TOC entry 221 (class 1259 OID 124471)
-- Name: classes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.classes (
    id bigint NOT NULL,
    teacher_id bigint,
    public_id uuid DEFAULT gen_random_uuid(),
    class_name text NOT NULL,
    description text,
    create_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.classes OWNER TO postgres;

--
-- TOC entry 222 (class 1259 OID 124480)
-- Name: classes_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.classes_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.classes_id_seq OWNER TO postgres;

--
-- TOC entry 5185 (class 0 OID 0)
-- Dependencies: 222
-- Name: classes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.classes_id_seq OWNED BY public.classes.id;


--
-- TOC entry 223 (class 1259 OID 124481)
-- Name: contest_results; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.contest_results (
    id bigint NOT NULL,
    student_id bigint,
    contest_id bigint,
    start_time timestamp without time zone,
    end_time timestamp without time zone,
    total_score numeric,
    count_wrong_answers integer,
    display_order text,
    guest_name character varying
);


ALTER TABLE public.contest_results OWNER TO postgres;

--
-- TOC entry 224 (class 1259 OID 124487)
-- Name: contest_results_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.contest_results_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.contest_results_id_seq OWNER TO postgres;

--
-- TOC entry 5186 (class 0 OID 0)
-- Dependencies: 224
-- Name: contest_results_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.contest_results_id_seq OWNED BY public.contest_results.id;


--
-- TOC entry 225 (class 1259 OID 124488)
-- Name: contests; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.contests (
    id bigint NOT NULL,
    class_id bigint,
    public_id uuid DEFAULT gen_random_uuid(),
    title text NOT NULL,
    time_limit integer NOT NULL,
    scoring_config jsonb,
    status character varying NOT NULL,
    teacher_id bigint,
    CONSTRAINT check_valid_status CHECK (((status)::text = ANY (ARRAY[('active'::character varying)::text, ('inactive'::character varying)::text, ('deleted'::character varying)::text])))
);


ALTER TABLE public.contests OWNER TO postgres;

--
-- TOC entry 226 (class 1259 OID 124499)
-- Name: contests_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.contests_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.contests_id_seq OWNER TO postgres;

--
-- TOC entry 5187 (class 0 OID 0)
-- Dependencies: 226
-- Name: contests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.contests_id_seq OWNED BY public.contests.id;


--
-- TOC entry 227 (class 1259 OID 124500)
-- Name: contests_questions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.contests_questions (
    contest_id bigint NOT NULL,
    question_id bigint NOT NULL,
    original_order integer,
    point_weight numeric
);


ALTER TABLE public.contests_questions OWNER TO postgres;

--
-- TOC entry 228 (class 1259 OID 124507)
-- Name: q_choice_details; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.q_choice_details (
    id bigint NOT NULL,
    question_id bigint,
    content text,
    is_correct boolean DEFAULT false NOT NULL,
    order_index integer NOT NULL,
    is_shufflable boolean DEFAULT true NOT NULL
);


ALTER TABLE public.q_choice_details OWNER TO postgres;

--
-- TOC entry 229 (class 1259 OID 124518)
-- Name: q_choice_details_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.q_choice_details_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.q_choice_details_id_seq OWNER TO postgres;

--
-- TOC entry 5188 (class 0 OID 0)
-- Dependencies: 229
-- Name: q_choice_details_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.q_choice_details_id_seq OWNED BY public.q_choice_details.id;


--
-- TOC entry 230 (class 1259 OID 124519)
-- Name: q_images; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.q_images (
    id bigint NOT NULL,
    question_id bigint,
    storage_path text,
    img_type character varying,
    img_scale numeric,
    raw_code text
);


ALTER TABLE public.q_images OWNER TO postgres;

--
-- TOC entry 231 (class 1259 OID 124525)
-- Name: q_images_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.q_images_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.q_images_id_seq OWNER TO postgres;

--
-- TOC entry 5189 (class 0 OID 0)
-- Dependencies: 231
-- Name: q_images_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.q_images_id_seq OWNED BY public.q_images.id;


--
-- TOC entry 232 (class 1259 OID 124526)
-- Name: q_shortans_details; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.q_shortans_details (
    id bigint NOT NULL,
    question_id bigint,
    content text
);


ALTER TABLE public.q_shortans_details OWNER TO postgres;

--
-- TOC entry 233 (class 1259 OID 124532)
-- Name: q_shortans_details_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.q_shortans_details_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.q_shortans_details_id_seq OWNER TO postgres;

--
-- TOC entry 5190 (class 0 OID 0)
-- Dependencies: 233
-- Name: q_shortans_details_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.q_shortans_details_id_seq OWNED BY public.q_shortans_details.id;


--
-- TOC entry 234 (class 1259 OID 124533)
-- Name: q_truefalse_details; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.q_truefalse_details (
    id bigint NOT NULL,
    question_id bigint,
    content text,
    is_correct boolean DEFAULT false NOT NULL,
    explaination text,
    order_index integer NOT NULL,
    is_shufflable boolean DEFAULT true NOT NULL
);


ALTER TABLE public.q_truefalse_details OWNER TO postgres;

--
-- TOC entry 235 (class 1259 OID 124544)
-- Name: q_truefalse_details_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.q_truefalse_details_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.q_truefalse_details_id_seq OWNER TO postgres;

--
-- TOC entry 5191 (class 0 OID 0)
-- Dependencies: 235
-- Name: q_truefalse_details_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.q_truefalse_details_id_seq OWNED BY public.q_truefalse_details.id;


--
-- TOC entry 236 (class 1259 OID 124545)
-- Name: questions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.questions (
    id bigint NOT NULL,
    teacher_id bigint,
    public_id uuid DEFAULT gen_random_uuid(),
    subject text,
    grade integer,
    parent_id bigint,
    question_type character varying,
    layout_type character varying,
    content text,
    solution text,
    chapter text,
    lesson text,
    complexity smallint,
    is_shufflable boolean,
    deleted_at timestamp without time zone
);


ALTER TABLE public.questions OWNER TO postgres;

--
-- TOC entry 237 (class 1259 OID 124552)
-- Name: questions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.questions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.questions_id_seq OWNER TO postgres;

--
-- TOC entry 5192 (class 0 OID 0)
-- Dependencies: 237
-- Name: questions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.questions_id_seq OWNED BY public.questions.id;


--
-- TOC entry 238 (class 1259 OID 124553)
-- Name: student_option_submissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.student_option_submissions (
    id bigint NOT NULL,
    contest_result_id bigint,
    question_id bigint,
    student_choice text,
    option_display_order text,
    is_correct boolean DEFAULT false,
    earned_point numeric(5,4) DEFAULT 0
);


ALTER TABLE public.student_option_submissions OWNER TO postgres;

--
-- TOC entry 239 (class 1259 OID 124561)
-- Name: student_option_submissions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.student_option_submissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.student_option_submissions_id_seq OWNER TO postgres;

--
-- TOC entry 5193 (class 0 OID 0)
-- Dependencies: 239
-- Name: student_option_submissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.student_option_submissions_id_seq OWNED BY public.student_option_submissions.id;


--
-- TOC entry 240 (class 1259 OID 124562)
-- Name: students; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.students (
    id bigint NOT NULL,
    school character varying
);


ALTER TABLE public.students OWNER TO postgres;

--
-- TOC entry 241 (class 1259 OID 124568)
-- Name: students_classes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.students_classes (
    student_id bigint NOT NULL,
    class_id bigint NOT NULL,
    create_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.students_classes OWNER TO postgres;

--
-- TOC entry 242 (class 1259 OID 124574)
-- Name: students_contests; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.students_contests (
    student_id bigint NOT NULL,
    contest_id bigint NOT NULL
);


ALTER TABLE public.students_contests OWNER TO postgres;

--
-- TOC entry 243 (class 1259 OID 124579)
-- Name: teachers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.teachers (
    id bigint NOT NULL,
    organization character varying
);


ALTER TABLE public.teachers OWNER TO postgres;

--
-- TOC entry 4921 (class 2604 OID 124585)
-- Name: accounts id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounts ALTER COLUMN id SET DEFAULT nextval('public.accounts_id_seq'::regclass);


--
-- TOC entry 4925 (class 2604 OID 124586)
-- Name: classes id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.classes ALTER COLUMN id SET DEFAULT nextval('public.classes_id_seq'::regclass);


--
-- TOC entry 4928 (class 2604 OID 124587)
-- Name: contest_results id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contest_results ALTER COLUMN id SET DEFAULT nextval('public.contest_results_id_seq'::regclass);


--
-- TOC entry 4929 (class 2604 OID 124588)
-- Name: contests id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contests ALTER COLUMN id SET DEFAULT nextval('public.contests_id_seq'::regclass);


--
-- TOC entry 4931 (class 2604 OID 124589)
-- Name: q_choice_details id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.q_choice_details ALTER COLUMN id SET DEFAULT nextval('public.q_choice_details_id_seq'::regclass);


--
-- TOC entry 4934 (class 2604 OID 124590)
-- Name: q_images id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.q_images ALTER COLUMN id SET DEFAULT nextval('public.q_images_id_seq'::regclass);


--
-- TOC entry 4935 (class 2604 OID 124591)
-- Name: q_shortans_details id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.q_shortans_details ALTER COLUMN id SET DEFAULT nextval('public.q_shortans_details_id_seq'::regclass);


--
-- TOC entry 4936 (class 2604 OID 124592)
-- Name: q_truefalse_details id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.q_truefalse_details ALTER COLUMN id SET DEFAULT nextval('public.q_truefalse_details_id_seq'::regclass);


--
-- TOC entry 4939 (class 2604 OID 124593)
-- Name: questions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questions ALTER COLUMN id SET DEFAULT nextval('public.questions_id_seq'::regclass);


--
-- TOC entry 4941 (class 2604 OID 124594)
-- Name: student_option_submissions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_option_submissions ALTER COLUMN id SET DEFAULT nextval('public.student_option_submissions_id_seq'::regclass);


--
-- TOC entry 5154 (class 0 OID 124456)
-- Dependencies: 219
-- Data for Name: accounts; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.accounts (id, public_id, email, password, is_active, role, name, avatar_url, create_at) FROM stdin;
\.


--
-- TOC entry 5156 (class 0 OID 124471)
-- Dependencies: 221
-- Data for Name: classes; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.classes (id, teacher_id, public_id, class_name, description, create_at) FROM stdin;
\.


--
-- TOC entry 5158 (class 0 OID 124481)
-- Dependencies: 223
-- Data for Name: contest_results; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.contest_results (id, student_id, contest_id, start_time, end_time, total_score, count_wrong_answers, display_order, guest_name) FROM stdin;
\.


--
-- TOC entry 5160 (class 0 OID 124488)
-- Dependencies: 225
-- Data for Name: contests; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.contests (id, class_id, public_id, title, time_limit, scoring_config, status, teacher_id) FROM stdin;
\.


--
-- TOC entry 5162 (class 0 OID 124500)
-- Dependencies: 227
-- Data for Name: contests_questions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.contests_questions (contest_id, question_id, original_order, point_weight, group_id) FROM stdin;
\.


--
-- TOC entry 5163 (class 0 OID 124507)
-- Dependencies: 228
-- Data for Name: q_choice_details; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.q_choice_details (id, question_id, content, is_correct, order_index, is_shufflable) FROM stdin;
\.


--
-- TOC entry 5165 (class 0 OID 124519)
-- Dependencies: 230
-- Data for Name: q_images; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.q_images (id, question_id, storage_path, img_type, img_scale, raw_code) FROM stdin;
\.


--
-- TOC entry 5167 (class 0 OID 124526)
-- Dependencies: 232
-- Data for Name: q_shortans_details; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.q_shortans_details (id, question_id, content) FROM stdin;
\.


--
-- TOC entry 5169 (class 0 OID 124533)
-- Dependencies: 234
-- Data for Name: q_truefalse_details; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.q_truefalse_details (id, question_id, content, is_correct, explaination, order_index, is_shufflable) FROM stdin;
\.


--
-- TOC entry 5171 (class 0 OID 124545)
-- Dependencies: 236
-- Data for Name: questions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.questions (id, teacher_id, public_id, subject, grade, parent_id, question_type, layout_type, content, solution, chapter, lesson, complexity, is_shufflable, deleted_at) FROM stdin;
\.


--
-- TOC entry 5173 (class 0 OID 124553)
-- Dependencies: 238
-- Data for Name: student_option_submissions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.student_option_submissions (id, contest_result_id, question_id, student_choice, option_display_order, is_correct, earned_point) FROM stdin;
\.


--
-- TOC entry 5175 (class 0 OID 124562)
-- Dependencies: 240
-- Data for Name: students; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.students (id, school) FROM stdin;
\.


--
-- TOC entry 5176 (class 0 OID 124568)
-- Dependencies: 241
-- Data for Name: students_classes; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.students_classes (student_id, class_id, create_at) FROM stdin;
\.


--
-- TOC entry 5177 (class 0 OID 124574)
-- Dependencies: 242
-- Data for Name: students_contests; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.students_contests (student_id, contest_id) FROM stdin;
\.


--
-- TOC entry 5178 (class 0 OID 124579)
-- Dependencies: 243
-- Data for Name: teachers; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.teachers (id, organization) FROM stdin;
\.


--
-- TOC entry 5194 (class 0 OID 0)
-- Dependencies: 220
-- Name: accounts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.accounts_id_seq', 102999, true);


--
-- TOC entry 5195 (class 0 OID 0)
-- Dependencies: 222
-- Name: classes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.classes_id_seq', 1001, true);


--
-- TOC entry 5196 (class 0 OID 0)
-- Dependencies: 224
-- Name: contest_results_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.contest_results_id_seq', 300713, true);


--
-- TOC entry 5197 (class 0 OID 0)
-- Dependencies: 226
-- Name: contests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.contests_id_seq', 1000, true);


--
-- TOC entry 5198 (class 0 OID 0)
-- Dependencies: 229
-- Name: q_choice_details_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.q_choice_details_id_seq', 5841084, true);


--
-- TOC entry 5199 (class 0 OID 0)
-- Dependencies: 231
-- Name: q_images_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.q_images_id_seq', 41314, true);


--
-- TOC entry 5200 (class 0 OID 0)
-- Dependencies: 233
-- Name: q_shortans_details_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.q_shortans_details_id_seq', 804484, true);


--
-- TOC entry 5201 (class 0 OID 0)
-- Dependencies: 235
-- Name: q_truefalse_details_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.q_truefalse_details_id_seq', 929136, true);


--
-- TOC entry 5202 (class 0 OID 0)
-- Dependencies: 237
-- Name: questions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.questions_id_seq', 3000000, true);


--
-- TOC entry 5203 (class 0 OID 0)
-- Dependencies: 239
-- Name: student_option_submissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.student_option_submissions_id_seq', 7368084, true);


--
-- TOC entry 4948 (class 2606 OID 124600)
-- Name: accounts accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounts
    ADD CONSTRAINT accounts_pkey PRIMARY KEY (id);


--
-- TOC entry 4950 (class 2606 OID 124602)
-- Name: accounts accounts_public_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounts
    ADD CONSTRAINT accounts_public_id_key UNIQUE (public_id);


--
-- TOC entry 4952 (class 2606 OID 124604)
-- Name: classes classes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.classes
    ADD CONSTRAINT classes_pkey PRIMARY KEY (id);


--
-- TOC entry 4954 (class 2606 OID 124606)
-- Name: classes classes_public_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.classes
    ADD CONSTRAINT classes_public_id_key UNIQUE (public_id);


--
-- TOC entry 4956 (class 2606 OID 124608)
-- Name: contest_results contest_results_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contest_results
    ADD CONSTRAINT contest_results_pkey PRIMARY KEY (id);


--
-- TOC entry 4958 (class 2606 OID 124610)
-- Name: contests contests_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contests
    ADD CONSTRAINT contests_pkey PRIMARY KEY (id);


--
-- TOC entry 4960 (class 2606 OID 124612)
-- Name: contests contests_public_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contests
    ADD CONSTRAINT contests_public_id_key UNIQUE (public_id);


--
-- TOC entry 4962 (class 2606 OID 124614)
-- Name: contests_questions pk_contests_questions; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contests_questions
    ADD CONSTRAINT pk_contests_questions PRIMARY KEY (contest_id, question_id);


--
-- TOC entry 4964 (class 2606 OID 124616)
-- Name: q_choice_details q_choice_details_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.q_choice_details
    ADD CONSTRAINT q_choice_details_pkey PRIMARY KEY (id);


--
-- TOC entry 4966 (class 2606 OID 124618)
-- Name: q_images q_images_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.q_images
    ADD CONSTRAINT q_images_pkey PRIMARY KEY (id);


--
-- TOC entry 4968 (class 2606 OID 124620)
-- Name: q_shortans_details q_shortans_details_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.q_shortans_details
    ADD CONSTRAINT q_shortans_details_pkey PRIMARY KEY (id);


--
-- TOC entry 4970 (class 2606 OID 124622)
-- Name: q_truefalse_details q_truefalse_details_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.q_truefalse_details
    ADD CONSTRAINT q_truefalse_details_pkey PRIMARY KEY (id);


--
-- TOC entry 4972 (class 2606 OID 124624)
-- Name: questions questions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questions
    ADD CONSTRAINT questions_pkey PRIMARY KEY (id);


--
-- TOC entry 4974 (class 2606 OID 124626)
-- Name: questions questions_public_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questions
    ADD CONSTRAINT questions_public_id_key UNIQUE (public_id);


--
-- TOC entry 4976 (class 2606 OID 124628)
-- Name: student_option_submissions student_option_submissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_option_submissions
    ADD CONSTRAINT student_option_submissions_pkey PRIMARY KEY (id);


--
-- TOC entry 4980 (class 2606 OID 124630)
-- Name: students_classes students_classes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.students_classes
    ADD CONSTRAINT students_classes_pkey PRIMARY KEY (student_id, class_id);


--
-- TOC entry 4982 (class 2606 OID 124632)
-- Name: students_contests students_contests_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.students_contests
    ADD CONSTRAINT students_contests_pkey PRIMARY KEY (student_id, contest_id);


--
-- TOC entry 4978 (class 2606 OID 124634)
-- Name: students students_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.students
    ADD CONSTRAINT students_pkey PRIMARY KEY (id);


--
-- TOC entry 4984 (class 2606 OID 124636)
-- Name: teachers teachers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teachers
    ADD CONSTRAINT teachers_pkey PRIMARY KEY (id);


--
-- TOC entry 4988 (class 2606 OID 181032)
-- Name: contests contests_fk_teachers; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contests
    ADD CONSTRAINT contests_fk_teachers FOREIGN KEY (teacher_id) REFERENCES public.teachers(id);


--
-- TOC entry 5001 (class 2606 OID 124638)
-- Name: students fk_account_student; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.students
    ADD CONSTRAINT fk_account_student FOREIGN KEY (id) REFERENCES public.accounts(id);


--
-- TOC entry 5006 (class 2606 OID 124643)
-- Name: teachers fk_account_teacher; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.teachers
    ADD CONSTRAINT fk_account_teacher FOREIGN KEY (id) REFERENCES public.accounts(id);



--
-- TOC entry 4991 (class 2606 OID 124653)
-- Name: contests_questions fk_contests_questions_contests; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contests_questions
    ADD CONSTRAINT fk_contests_questions_contests FOREIGN KEY (contest_id) REFERENCES public.contests(id) ON DELETE CASCADE;


--
-- TOC entry 4992 (class 2606 OID 124658)
-- Name: contests_questions fk_contests_questions_questions; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contests_questions
    ADD CONSTRAINT fk_contests_questions_questions FOREIGN KEY (question_id) REFERENCES public.questions(id) ON DELETE CASCADE;


--
-- TOC entry 4990 (class 2606 OID 181027)
-- Name: contests fk_contests_teacher; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contests
    ADD CONSTRAINT fk_contests_teacher FOREIGN KEY (teacher_id) REFERENCES public.teachers(id);


--
-- TOC entry 4997 (class 2606 OID 124663)
-- Name: questions fk_parent_question; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questions
    ADD CONSTRAINT fk_parent_question FOREIGN KEY (parent_id) REFERENCES public.questions(id);


--
-- TOC entry 4993 (class 2606 OID 124668)
-- Name: q_choice_details fk_question_images; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.q_choice_details
    ADD CONSTRAINT fk_question_images FOREIGN KEY (question_id) REFERENCES public.questions(id);


--
-- TOC entry 4994 (class 2606 OID 124673)
-- Name: q_images fk_question_images; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.q_images
    ADD CONSTRAINT fk_question_images FOREIGN KEY (question_id) REFERENCES public.questions(id);


--
-- TOC entry 4995 (class 2606 OID 124678)
-- Name: q_shortans_details fk_question_images; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.q_shortans_details
    ADD CONSTRAINT fk_question_images FOREIGN KEY (question_id) REFERENCES public.questions(id);


--
-- TOC entry 4996 (class 2606 OID 124683)
-- Name: q_truefalse_details fk_question_images; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.q_truefalse_details
    ADD CONSTRAINT fk_question_images FOREIGN KEY (question_id) REFERENCES public.questions(id);


--
-- TOC entry 4998 (class 2606 OID 124688)
-- Name: questions fk_questions_teacher; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questions
    ADD CONSTRAINT fk_questions_teacher FOREIGN KEY (teacher_id) REFERENCES public.teachers(id);


--
-- TOC entry 4999 (class 2606 OID 124693)
-- Name: student_option_submissions fk_student_option_submissions_contest_results; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_option_submissions
    ADD CONSTRAINT fk_student_option_submissions_contest_results FOREIGN KEY (contest_result_id) REFERENCES public.contest_results(id);


--
-- TOC entry 5000 (class 2606 OID 124698)
-- Name: student_option_submissions fk_student_option_submissions_questions; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.student_option_submissions
    ADD CONSTRAINT fk_student_option_submissions_questions FOREIGN KEY (question_id) REFERENCES public.questions(id);


--
-- TOC entry 5002 (class 2606 OID 124703)
-- Name: students_classes fk_students_classes_classes; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.students_classes
    ADD CONSTRAINT fk_students_classes_classes FOREIGN KEY (class_id) REFERENCES public.classes(id);


--
-- TOC entry 5003 (class 2606 OID 124708)
-- Name: students_classes fk_students_classes_students; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.students_classes
    ADD CONSTRAINT fk_students_classes_students FOREIGN KEY (student_id) REFERENCES public.students(id);


--
-- TOC entry 4986 (class 2606 OID 124713)
-- Name: contest_results fk_students_contests_contests; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contest_results
    ADD CONSTRAINT fk_students_contests_contests FOREIGN KEY (contest_id) REFERENCES public.contests(id);


--
-- TOC entry 5004 (class 2606 OID 124718)
-- Name: students_contests fk_students_contests_contests; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.students_contests
    ADD CONSTRAINT fk_students_contests_contests FOREIGN KEY (contest_id) REFERENCES public.contests(id);


--
-- TOC entry 4987 (class 2606 OID 124723)
-- Name: contest_results fk_students_contests_students; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contest_results
    ADD CONSTRAINT fk_students_contests_students FOREIGN KEY (student_id) REFERENCES public.students(id);


--
-- TOC entry 5005 (class 2606 OID 124728)
-- Name: students_contests fk_students_contests_students; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.students_contests
    ADD CONSTRAINT fk_students_contests_students FOREIGN KEY (student_id) REFERENCES public.students(id);


--
-- TOC entry 4985 (class 2606 OID 124733)
-- Name: classes fk_teacher_classes; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.classes
    ADD CONSTRAINT fk_teacher_classes FOREIGN KEY (teacher_id) REFERENCES public.teachers(id);


-- Completed on 2026-06-09 16:35:15

--
-- PostgreSQL database dump complete
--

\unrestrict 8FaRNXGi1Drc4LxOKKhOMalfVjTAlXmgKXbJbdZiTHcUtGDMLgyb4MpS6TsJlHC

