--
-- PostgreSQL database dump
--

-- Dumped from database version 16.1
-- Dumped by pg_dump version 16.1

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: faculties; Type: TABLE DATA; Schema: public; Owner: walker
--

COPY public.faculties (id, name, total_points) FROM stdin;
2	Пакваджи	66
3	Птица Гром	45
4	Рогатый змей	15
1	Вампус	5
\.


--
-- Data for Name: points_transactions; Type: TABLE DATA; Schema: public; Owner: walker
--

COPY public.points_transactions (id, faculty_id, points, sender_name, sender_surname, "timestamp") FROM stdin;
1	3	5	Брут	Айзенгард	2023-12-09 23:05:58.911257
2	3	15	Брут	Айзенгард	2023-12-09 23:06:06.051365
3	3	10	Брут	Айзенгард	2023-12-09 23:06:09.629295
4	3	10	Брут	Айзенгард	2023-12-09 23:06:12.593186
18	4	15	Ш	П	2023-12-10 01:45:01.46858
21	2	15	gcgcgg.	gmnvgcvg	2023-12-13 16:45:09.465001
22	2	15	Брут	Айзенгард	2023-12-13 16:51:13.176516
23	2	10	Брут	Айзенгард	2023-12-13 16:51:15.316892
24	2	5	Брут	Айзенгард	2023-12-13 16:51:17.691716
25	2	15	Брут	Айзенгард	2023-12-13 16:51:20.014119
36	2	15	Брут	Айзенгард	2023-12-13 18:14:10.868331
37	2	15	Брут	Айзенгард	2023-12-13 18:14:12.839302
5	3	10	Брут	Айзенгард	2023-12-09 23:08:26.111351
6	3	10	Брут	Айзенгард	2023-12-09 23:08:28.92893
7	3	15	Брут	Айзенгард	2023-12-09 23:08:31.483396
8	4	10	Брут	Айзенгард	2023-12-09 23:08:35.20784
9	2	1	Брут	Айзенгард	2023-12-09 23:08:39.964457
10	1	10	Брут	Айзенгард	2023-12-09 23:08:45.227884
11	3	15	в	м	2023-12-09 23:24:26.812242
12	3	15	в	м	2023-12-09 23:24:33.770846
13	3	15	в	м	2023-12-09 23:24:39.967567
14	3	15	в	м	2023-12-09 23:24:42.669456
15	3	10	Брут	Айзенгард	2023-12-09 23:49:06.147911
16	3	5	Брут	Айзенгард	2023-12-09 23:49:10.486129
17	3	15	Брут	Айзенгард	2023-12-09 23:49:14.563821
19	4	15	A	S	2023-12-11 21:42:28.960191
20	4	5	A	S	2023-12-11 21:42:35.553164
27	1	15	Брут	Айзенгард	2023-12-13 16:54:33.110438
28	1	15	Брут	Айзенгард	2023-12-13 16:54:35.820241
29	1	10	Брут	Айзенгард	2023-12-13 16:54:39.653466
30	1	10	Брут	Айзенгард	2023-12-13 16:54:42.215149
31	1	15	Брут	Айзенгард	2023-12-13 16:54:45.810823
32	1	1	Брут	Айзенгард	2023-12-13 16:54:57.496433
33	1	1	Брут	Айзенгард	2023-12-13 16:54:59.257337
34	2	15	вавмв	фвафы	2023-12-13 17:58:16.378295
35	4	15	вавмв	фвафы	2023-12-13 18:00:36.623345
26	4	15	С	ЫЫ	2023-12-13 16:52:51.626863
\.


--
-- Name: faculties_id_seq; Type: SEQUENCE SET; Schema: public; Owner: walker
--

SELECT pg_catalog.setval('public.faculties_id_seq', 4, true);


--
-- Name: points_transactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: walker
--

SELECT pg_catalog.setval('public.points_transactions_id_seq', 35, true);


--
-- PostgreSQL database dump complete
--

