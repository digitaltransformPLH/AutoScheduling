-- 006_store_org_seed.sql
-- Person, AmOmAssignment, Store org data from Danh sách CH PLH - 2026
SET NOCOUNT ON;

-- Persons
SET IDENTITY_INSERT dbo.Persons ON;
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 1) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (1, N'Bùi Tuấn Anh', N'anhbt1@phuclong.masangroup.com', N'898318428.0', N'AM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 2) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (2, N'Group mail GSKV', N'pl.gskv@phuclong.masangroup.com', NULL, N'AM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 3) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (3, N'Lưu Hồng Phương Thảo', N'thaolhp@phuclong.masangroup.com', N'909228344.0', N'AM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 4) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (4, N'Nguyễn Chí Nhân', N'nhannc2@phuclong.masangroup.com', N'946050414.0', N'AM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 5) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (5, N'Nguyễn Thanh Phát', N'phatnt8@phuclong.masangroup.com', N'909554815.0', N'AM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 6) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (6, N'Nguyễn Thiện Hải', N'haint10@phuclong.masangroup.com', N'388721222.0', N'AM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 7) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (7, N'Nguyễn Thị Hà Giang', N'giangnth@phuclong.masangroup.com', N'374244500.0', N'AM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 8) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (8, N'Nguyễn Thị Khuynh Diệp', N'diepntk@phuclong.masangroup.com', N'935835638.0', N'AM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 9) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (9, N'Nguyễn Thị Minh Hiền', N'hienntm@phuclong.masangroup.com', N'393232664.0', N'AM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 10) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (10, N'Nguyễn Thị Trúc Linh', N'linhntt3@phuclong.masangroup.com', N'978478523.0', N'AM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 11) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (11, N'Nguyễn Võ Phương Nam', N'namnvp@phuclong.masangroup.com', N'941651016.0', N'AM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 12) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (12, N'Phan Minh Son', N'sonpm@phuclong.masangroup.com', N'396703799.0', N'AM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 13) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (13, N'Phan Thị Thùy Linh', N'linhptt2@phuclong.masangroup.com', N'559838068.0', N'AM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 14) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (14, N'Phạm Chí Thiện', N'thienpc@phuclong.masangroup.com', N'767113029.0', N'AM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 15) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (15, N'Thái Thành Danh', N'danhtt@phuclong.masangroup.com', N'987058894.0', N'AM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 16) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (16, N'Trương Hằng Nga', N'ngath@phuclong.masangroup.com', N'938072695.0', N'AM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 17) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (17, N'Trương Tịnh Khang', N'khangtt1@phuclong.masangroup.com', N'387565292.0', N'AM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 18) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (18, N'Trần Nguyệt Thảo', N'thaotn@phuclong.masangroup.com', N'785979179.0', N'AM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 19) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (19, N'Trần Ngọc Thanh Nhân', N'nhantnt@phuclong.masangroup.com', N'902299127.0', N'AM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 20) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (20, N'Trần Thị Thùy Linh', N'linhttt@phuclong.masangroup.com', N'818025228.0', N'AM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 21) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (21, N'Vũ Thị Hoàng Phương', N'phuongvth@phuclong.masangroup.com', N'972500507.0', N'AM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 22) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (22, N'Đinh Thị Kim Tuyến', N'tuyendtk@phuclong.masangroup.com', N'976411144.0', N'AM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 23) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (23, N'Đào Hồng Yến Ngân', N'ngandhy@phuclong.masangroup.com', N'909543251.0', N'AM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 24) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (24, N'Anna Nguyen', N'tuyetnty@phuclong.masangroup.com', N'908524518.0', N'ROM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 25) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (25, N'Nguyễn Thị Trúc Linh', NULL, NULL, N'ROM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 26) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (26, N'Nguyễn Thị Yến Tuyết (Anna Nguyễn)', NULL, NULL, N'ROM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 27) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (27, N'Phạm Ngọc Minh', N'minhpn@phuclong.masangroup.com', N'979471396.0', N'ROM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 28) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (28, N'Trần Ngọc Thanh Nhân', NULL, NULL, N'ROM', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.Persons WHERE Id = 29) INSERT INTO dbo.Persons (Id, FullName, Email, Phone, Role, IsActive) VALUES (29, N'Trần Vĩnh Thịnh', N'thinhtv1@phuclong.masangroup.com', N'767360629.0', N'ROM', 1);
SET IDENTITY_INSERT dbo.Persons OFF;

-- AmOmAssignments (current)
SET IDENTITY_INSERT dbo.AmOmAssignments ON;
IF NOT EXISTS (SELECT 1 FROM dbo.AmOmAssignments WHERE Id = 1) INSERT INTO dbo.AmOmAssignments (Id, AreaManagerId, OperationManagerId, EffectiveFrom, EffectiveTo) VALUES (1, 1, 25, '2026-06-01', NULL);
IF NOT EXISTS (SELECT 1 FROM dbo.AmOmAssignments WHERE Id = 2) INSERT INTO dbo.AmOmAssignments (Id, AreaManagerId, OperationManagerId, EffectiveFrom, EffectiveTo) VALUES (2, 3, 29, '2026-06-01', NULL);
IF NOT EXISTS (SELECT 1 FROM dbo.AmOmAssignments WHERE Id = 3) INSERT INTO dbo.AmOmAssignments (Id, AreaManagerId, OperationManagerId, EffectiveFrom, EffectiveTo) VALUES (3, 4, 25, '2026-06-01', NULL);
IF NOT EXISTS (SELECT 1 FROM dbo.AmOmAssignments WHERE Id = 4) INSERT INTO dbo.AmOmAssignments (Id, AreaManagerId, OperationManagerId, EffectiveFrom, EffectiveTo) VALUES (4, 5, 25, '2026-06-01', NULL);
IF NOT EXISTS (SELECT 1 FROM dbo.AmOmAssignments WHERE Id = 5) INSERT INTO dbo.AmOmAssignments (Id, AreaManagerId, OperationManagerId, EffectiveFrom, EffectiveTo) VALUES (5, 6, 27, '2026-06-01', NULL);
IF NOT EXISTS (SELECT 1 FROM dbo.AmOmAssignments WHERE Id = 6) INSERT INTO dbo.AmOmAssignments (Id, AreaManagerId, OperationManagerId, EffectiveFrom, EffectiveTo) VALUES (6, 7, 26, '2026-06-01', NULL);
IF NOT EXISTS (SELECT 1 FROM dbo.AmOmAssignments WHERE Id = 7) INSERT INTO dbo.AmOmAssignments (Id, AreaManagerId, OperationManagerId, EffectiveFrom, EffectiveTo) VALUES (7, 8, 26, '2026-06-01', NULL);
IF NOT EXISTS (SELECT 1 FROM dbo.AmOmAssignments WHERE Id = 8) INSERT INTO dbo.AmOmAssignments (Id, AreaManagerId, OperationManagerId, EffectiveFrom, EffectiveTo) VALUES (8, 9, 29, '2026-06-01', NULL);
IF NOT EXISTS (SELECT 1 FROM dbo.AmOmAssignments WHERE Id = 9) INSERT INTO dbo.AmOmAssignments (Id, AreaManagerId, OperationManagerId, EffectiveFrom, EffectiveTo) VALUES (9, 11, 25, '2026-06-01', NULL);
IF NOT EXISTS (SELECT 1 FROM dbo.AmOmAssignments WHERE Id = 10) INSERT INTO dbo.AmOmAssignments (Id, AreaManagerId, OperationManagerId, EffectiveFrom, EffectiveTo) VALUES (10, 12, 26, '2026-06-01', NULL);
IF NOT EXISTS (SELECT 1 FROM dbo.AmOmAssignments WHERE Id = 11) INSERT INTO dbo.AmOmAssignments (Id, AreaManagerId, OperationManagerId, EffectiveFrom, EffectiveTo) VALUES (11, 13, 26, '2026-06-01', NULL);
IF NOT EXISTS (SELECT 1 FROM dbo.AmOmAssignments WHERE Id = 12) INSERT INTO dbo.AmOmAssignments (Id, AreaManagerId, OperationManagerId, EffectiveFrom, EffectiveTo) VALUES (12, 14, 26, '2026-06-01', NULL);
IF NOT EXISTS (SELECT 1 FROM dbo.AmOmAssignments WHERE Id = 13) INSERT INTO dbo.AmOmAssignments (Id, AreaManagerId, OperationManagerId, EffectiveFrom, EffectiveTo) VALUES (13, 15, 29, '2026-06-01', NULL);
IF NOT EXISTS (SELECT 1 FROM dbo.AmOmAssignments WHERE Id = 14) INSERT INTO dbo.AmOmAssignments (Id, AreaManagerId, OperationManagerId, EffectiveFrom, EffectiveTo) VALUES (14, 16, 29, '2026-06-01', NULL);
IF NOT EXISTS (SELECT 1 FROM dbo.AmOmAssignments WHERE Id = 15) INSERT INTO dbo.AmOmAssignments (Id, AreaManagerId, OperationManagerId, EffectiveFrom, EffectiveTo) VALUES (15, 17, 29, '2026-06-01', NULL);
IF NOT EXISTS (SELECT 1 FROM dbo.AmOmAssignments WHERE Id = 16) INSERT INTO dbo.AmOmAssignments (Id, AreaManagerId, OperationManagerId, EffectiveFrom, EffectiveTo) VALUES (16, 18, 29, '2026-06-01', NULL);
IF NOT EXISTS (SELECT 1 FROM dbo.AmOmAssignments WHERE Id = 17) INSERT INTO dbo.AmOmAssignments (Id, AreaManagerId, OperationManagerId, EffectiveFrom, EffectiveTo) VALUES (17, 20, 27, '2026-06-01', NULL);
IF NOT EXISTS (SELECT 1 FROM dbo.AmOmAssignments WHERE Id = 18) INSERT INTO dbo.AmOmAssignments (Id, AreaManagerId, OperationManagerId, EffectiveFrom, EffectiveTo) VALUES (18, 21, 27, '2026-06-01', NULL);
IF NOT EXISTS (SELECT 1 FROM dbo.AmOmAssignments WHERE Id = 19) INSERT INTO dbo.AmOmAssignments (Id, AreaManagerId, OperationManagerId, EffectiveFrom, EffectiveTo) VALUES (19, 22, 27, '2026-06-01', NULL);
IF NOT EXISTS (SELECT 1 FROM dbo.AmOmAssignments WHERE Id = 20) INSERT INTO dbo.AmOmAssignments (Id, AreaManagerId, OperationManagerId, EffectiveFrom, EffectiveTo) VALUES (20, 23, 27, '2026-06-01', NULL);
SET IDENTITY_INSERT dbo.AmOmAssignments OFF;

-- Stores MERGE
MERGE dbo.Stores AS t
USING (
VALUES
    (N'3196', N'HCM - Mplaza 39 Lê Duẩn (CH lớn có chỗ ngồi)', N'TP. Hồ Chí Minh', NULL, '2021-10-15', N'Pl.3196@phuclong.masangroup.com', 13, 1),
    (N'3385', N'HNI - Vinmart Cầu Giấy (CH lớn có chỗ ngồi)', N'TP. Hà Nội', NULL, '2021-12-22', N'Pl.3385@phuclong.masangroup.com', 20, 1),
    (N'3101', N'HNI - Vinmart Hà Đông (CH lớn có chỗ ngồi)', N'TP. Hà Nội', NULL, '2021-11-15', N'Pl.3101@phuclong.masangroup.com', 21, 1),
    (N'2001', N'BDG-CH AEON Binh Duong P.Bình Hòa', N'T. Bình Dương', NULL, '2014-11-01', N'Pl.2001@phuclong.masangroup.com', 9, 1),
    (N'2002', N'BDG-CH 44 Nguyen Dinh Chieu P.PC', N'T. Bình Dương', NULL, '2018-06-29', N'Pl.2002@phuclong.masangroup.com', 9, 1),
    (N'2003', N'CTO-CH Vincom Hung Vuong Số 2 HV', N'TP. Cần Thơ', NULL, '2019-08-26', N'Pl.2003@phuclong.masangroup.com', 4, 1),
    (N'2004', N'CTO-CH 314 Đường 30.4 P.HL Q.Ninh Kiều', N'TP. Cần Thơ', NULL, '2019-07-28', N'Pl.2004@phuclong.masangroup.com', 4, 1),
    (N'2005', N'DNG-CH Lotte Số 6 Đại Nam P.HCB', N'TP. Đà Nẵng', NULL, '2018-04-20', N'Pl.2005@phuclong.masangroup.com', 22, 1),
    (N'2006', N'DNG-CH 59-61 Nguyen Van Linh P.PN', N'TP. Đà Nẵng', NULL, '2018-06-15', N'Pl.2006@phuclong.masangroup.com', 22, 1),
    (N'2007', N'DNI-CH 217 Vo Thi Sau P.TN', N'T. Đồng Nai', NULL, '2019-08-22', N'Pl.2007@phuclong.masangroup.com', 9, 1),
    (N'2009', N'HNI-CH 82-84 Hàng Điếu P.CĐ', N'TP. Hà Nội', NULL, '2019-05-02', N'Pl.2009@phuclong.masangroup.com', 6, 1),
    (N'2010', N'HNI-CH Golden Palm 21 LVL P.NC', N'TP. Hà Nội', NULL, '2020-08-12', N'Pl.2010@phuclong.masangroup.com', 23, 1),
    (N'2013', N'HNI-CH Số 5 Ngõ 30 Tạ Quang Bửu', N'TP. Hà Nội', NULL, '2020-04-23', N'Pl.2013@phuclong.masangroup.com', 6, 1),
    (N'2014', N'HNI-CH 66-68 Tran Xuan Soan P.NTN', N'TP. Hà Nội', NULL, '2019-12-06', N'Pl.2014@phuclong.masangroup.com', 6, 1),
    (N'2015', N'HNI-CH NewSkyline, P.Văn Quán', N'TP. Hà Nội', NULL, '2019-11-18', N'Pl.2015@phuclong.masangroup.com', 21, 1),
    (N'2017', N'HCM-CH Lotte 968 Đường 3/2 P.15 Q11', N'TP. Hồ Chí Minh', NULL, '2017-12-15', N'Pl.2017@phuclong.masangroup.com', 16, 1),
    (N'2018', N'HCM-CH Aeon Binh Tan Số 1 Đường', N'TP. Hồ Chí Minh', NULL, '2016-07-01', N'Pl.2018@phuclong.masangroup.com', 11, 1),
    (N'2019', N'HCM-CH 681 Au Co P.TT Q.TP', N'TP. Hồ Chí Minh', NULL, '2020-10-15', N'Pl.2019@phuclong.masangroup.com', 18, 1),
    (N'2020', N'HCM-CH 76 Ba Hom P.13 Q6', N'TP. Hồ Chí Minh', NULL, '2018-11-30', N'Pl.2020@phuclong.masangroup.com', 16, 1),
    (N'2021', N'HCM-CH Gold View 346 Bến Vân Đồn', N'TP. Hồ Chí Minh', NULL, '2019-10-15', N'Pl.2021@phuclong.masangroup.com', 16, 1),
    (N'2023', N'HCM-CH 1B Cong Hoa P4 Q.TB', N'TP. Hồ Chí Minh', NULL, '2016-05-10', N'Pl.2023@phuclong.masangroup.com', 5, 1),
    (N'2024', N'HCM-CH Republic 18E Cong Hoa P4', N'TP. Hồ Chí Minh', NULL, '2019-04-12', N'Pl.2024@phuclong.masangroup.com', 5, 1),
    (N'2025', N'HCM-CH VNG CAMPUS Z06 Đường Số 1', N'TP. Hồ Chí Minh', NULL, '2021-11-01', N'Pl.2025@phuclong.masangroup.com', 13, 1),
    (N'2026', N'HCM-CH Đường số 7 P.Bình Trị Đông', N'TP. Hồ Chí Minh', NULL, '2021-03-19', N'Pl.2026@phuclong.masangroup.com', 11, 1),
    (N'2027', N'HCM-CH 197 Dinh Tien Hoang P.TĐ Q1', N'TP. Hồ Chí Minh', NULL, '2018-04-27', N'Pl.2027@phuclong.masangroup.com', 15, 1),
    (N'2030', N'HCM-CH 26 Huỳnh Thúc Kháng P.BN Q1', N'TP. Hồ Chí Minh', NULL, '2016-12-16', N'Pl.2030@phuclong.masangroup.com', 18, 1),
    (N'2032', N'HCM-CH 24 Lê Đức Thọ P.7 Q.GV', N'TP. Hồ Chí Minh', NULL, '2021-12-24', N'Pl.2032@phuclong.masangroup.com', 5, 1),
    (N'2034', N'HCM-CH Saigon Centre 67 Lê Lợi', N'TP. Hồ Chí Minh', NULL, '2019-09-27', N'Pl.2034@phuclong.masangroup.com', 18, 1),
    (N'2035', N'HCM-CH Vincom Landmark 772 ĐBP', N'TP. Hồ Chí Minh', NULL, '2018-07-26', N'Pl.2035@phuclong.masangroup.com', 3, 1),
    (N'2036', N'HCM-CH 4-4A Le Quang Sung P6 Q6', N'TP. Hồ Chí Minh', NULL, '2019-07-06', N'Pl.2036@phuclong.masangroup.com', 16, 1),
    (N'2037', N'HCM-CH 247-249 Ly Thuong Kiet P6', N'TP. Hồ Chí Minh', NULL, '2019-12-20', N'Pl.2037@phuclong.masangroup.com', 5, 1),
    (N'2039', N'HCM-CH 592 Le Van Luong P.TP Q7', N'TP. Hồ Chí Minh', NULL, '2020-09-20', N'Pl.2039@phuclong.masangroup.com', 13, 1),
    (N'2040', N'HCM-CH 350 Le Van Si P.14 Q3', N'TP. Hồ Chí Minh', NULL, '1998-05-05', N'Pl.2040@phuclong.masangroup.com', 14, 1),
    (N'2041', N'HCM-CH 63 Mạc Thị Bưởi P.BN Q1', N'TP. Hồ Chí Minh', NULL, '2005-12-07', N'Pl.2041@phuclong.masangroup.com', 18, 1),
    (N'2042', N'HCM-CH Romea 117 Nguyen Dinh', N'TP. Hồ Chí Minh', NULL, '2017-04-27', N'Pl.2042@phuclong.masangroup.com', 14, 1),
    (N'2045', N'HCM-CH Gollden Plaza 922NT P.14 Q5', N'TP. Hồ Chí Minh', NULL, '2017-02-25', N'Pl.2045@phuclong.masangroup.com', 12, 1),
    (N'2046', N'HCM-CH 317 Ngô Gia Tự P3 Q.10', N'TP. Hồ Chí Minh', NULL, '2019-08-18', N'Pl.2046@phuclong.masangroup.com', 12, 1),
    (N'2047', N'HCM-CH 157-159 Nguyễn Thái Học', N'TP. Hồ Chí Minh', NULL, '2016-08-19', N'Pl.2047@phuclong.masangroup.com', 15, 1),
    (N'2048', N'HCM-CH Lotte 469 KHA P.TH Q7', N'TP. Hồ Chí Minh', NULL, '2017-04-21', N'Pl.2048@phuclong.masangroup.com', 13, 1),
    (N'2050', N'HCM-CH 21 Nguyễn Thị Minh Khai', N'TP. Hồ Chí Minh', NULL, '2017-01-22', N'Pl.2050@phuclong.masangroup.com', 15, 1),
    (N'2051', N'HCM-CH Nowzone 235 NVC P.NCT Q1', N'TP. Hồ Chí Minh', NULL, '2015-11-11', N'Pl.2051@phuclong.masangroup.com', 15, 1),
    (N'2052', N'HCM-CH CENTRE POINT 106 NVT P8 Q.PN', N'TP. Hồ Chí Minh', NULL, '2013-02-25', N'Pl.2052@phuclong.masangroup.com', 14, 1),
    (N'2053', N'HCM-CH 119C Pho Quang P9 Q.PN', N'TP. Hồ Chí Minh', NULL, '2019-07-28', N'Pl.2053@phuclong.masangroup.com', 14, 1),
    (N'2054', N'HCM-CH 42 Phạm Hồng Thái P.BT Q1', N'TP. Hồ Chí Minh', NULL, '2016-01-25', N'Pl.2054@phuclong.masangroup.com', 15, 1),
    (N'2055', N'HCM-CH Giga Mall 240 PVĐ P.HBC', N'TP. Hồ Chí Minh', NULL, '2019-11-15', N'Pl.2055@phuclong.masangroup.com', 8, 1),
    (N'2057', N'HCM-CH 672A25 PHNI Văn Trị P.10', N'TP. Hồ Chí Minh', NULL, '2021-02-09', N'Pl.2057@phuclong.masangroup.com', 1, 1),
    (N'2058', N'HCM-CH 95 PHNI Xich Long P2 Q.PN', N'TP. Hồ Chí Minh', NULL, '2020-11-13', N'Pl.2058@phuclong.masangroup.com', 14, 1),
    (N'2059', N'HCM-CH Vincom 190 Quang Trung', N'TP. Hồ Chí Minh', NULL, '2018-09-01', N'Pl.2059@phuclong.masangroup.com', 1, 1),
    (N'2060', N'HCM-CH Estella 88 Song Hành P.AP Q2', N'TP. Hồ Chí Minh', NULL, '2018-12-15', N'Pl.2060@phuclong.masangroup.com', 7, 1),
    (N'2061', N'HCM-CH Co.op 11 Su Van Hạnh P2 Q.10', N'TP. Hồ Chí Minh', NULL, '2018-01-27', N'Pl.2061@phuclong.masangroup.com', 12, 1),
    (N'2062', N'HCM-CH 812 Sư Vạn Hạnh P.12 Q.10', N'TP. Hồ Chí Minh', NULL, '2021-05-17', N'Pl.2062@phuclong.masangroup.com', 12, 1),
    (N'2063', N'HCM-CH 42 Trần Cao Vân P6 Q3', N'TP. Hồ Chí Minh', NULL, '2017-11-18', N'Pl.2063@phuclong.masangroup.com', 14, 1),
    (N'2064', N'HCM-CH Crescent Mall 101 TDT P.TP', N'TP. Hồ Chí Minh', NULL, '2012-06-01', N'Pl.2064@phuclong.masangroup.com', 13, 1),
    (N'2066', N'HCM-CH 188 Tran Hung Dao P.11 Quận 5', N'TP. Hồ Chí Minh', NULL, '2002-12-23', N'Pl.2066@phuclong.masangroup.com', 12, 1),
    (N'2067', N'HCM-CH 218A Thành Thái P.14 Q.10', N'TP. Hồ Chí Minh', NULL, '2018-05-04', N'Pl.2067@phuclong.masangroup.com', 12, 1),
    (N'2068', N'HCM-CH 46 Tran Quang Khai P.TĐ Q1', N'TP. Hồ Chí Minh', NULL, '2019-10-10', N'Pl.2068@phuclong.masangroup.com', 15, 1),
    (N'2069', N'HCM-CH 493A Truong Chinh P.14 Q.TB', N'TP. Hồ Chí Minh', NULL, '2018-01-11', N'Pl.2069@phuclong.masangroup.com', 5, 1),
    (N'2070', N'HCM-CH Coop Thắng Lợi, 2 TRC', N'TP. Hồ Chí Minh', NULL, '2021-05-29', N'Pl.2070@phuclong.masangroup.com', 18, 1),
    (N'2071', N'HCM-CH Vietjet Plaza 60 Trường Sơn', N'TP. Hồ Chí Minh', NULL, '2019-09-06', N'Pl.2071@phuclong.masangroup.com', 5, 1),
    (N'2072', N'HCM-CH TSN QN- Tang 1-Gate 9', N'TP. Hồ Chí Minh', NULL, '2019-08-15', N'Pl.2072@phuclong.masangroup.com', 5, 1),
    (N'2077', N'HCM-CH TSN Gate 3-4-17 Quốc Tế', N'TP. Hồ Chí Minh', NULL, '2019-08-15', N'Pl.2077@phuclong.masangroup.com', 5, 1),
    (N'2078', N'HCM-CH 329 Truong Vinh Ky P.TT', N'TP. Hồ Chí Minh', NULL, '2019-11-29', N'Pl.2078@phuclong.masangroup.com', 11, 1),
    (N'2079', N'HCM-CH BV Nhi 15 Võ Trần Chí X.TK', N'TP. Hồ Chí Minh', NULL, '2018-05-26', N'Pl.2079@phuclong.masangroup.com', 11, 1),
    (N'2080', N'LDG-CH 28 Tran Phu P4 TP.Đà Lạt', N'T. Lâm Đồng', NULL, '2020-05-11', N'Pl.2080@phuclong.masangroup.com', 17, 1),
    (N'2082', N'KHA-CH 78-80 Trần Phú P.Lộc Thọ', N'T. Khánh Hòa', NULL, '2018-08-15', N'Pl.2082@phuclong.masangroup.com', 17, 1),
    (N'2083', N'HCM-CH 183F Trần Quốc Thảo', N'TP. Hồ Chí Minh', NULL, '2022-03-05', N'Pl.2083@phuclong.masangroup.com', 14, 1),
    (N'2084', N'KHA-CH 20 Trần Phú, TP.Nha Trang', N'T. Khánh Hòa', NULL, '2022-04-30', N'Pl.2084@phuclong.masangroup.com', 17, 1),
    (N'2087', N'HCM VM Dimond (CH lớn có chỗ ngồi)', N'TP. Hồ Chí Minh', NULL, '2022-04-30', N'Pl.2087@phuclong.masangroup.com', 7, 1),
    (N'2090', N'CTO VM Ninh Kiều (CH lớn có chỗ ngồi)', N'TP. Cần Thơ', NULL, '2022-04-28', N'Pl.2090@phuclong.masangroup.com', 4, 1),
    (N'2091', N'HCM-CH 46 Cần Giuộc', N'TP. Hồ Chí Minh', NULL, '2022-04-27', N'Pl.2091@phuclong.masangroup.com', 12, 1),
    (N'2092', N'LDG-CH 30 Trương Công Định', N'T. Lâm Đồng', NULL, '2022-05-15', N'Pl.2092@phuclong.masangroup.com', 17, 1),
    (N'2093', N'HCM-CH 481 Nguyễn Tri Phương', N'TP. Hồ Chí Minh', NULL, '2022-06-29', N'Pl.2093@phuclong.masangroup.com', 12, 1),
    (N'2094', N'HCM-CH 68 Lê Văn Khương', N'TP. Hồ Chí Minh', NULL, '2022-08-01', N'Pl.2094@phuclong.masangroup.com', 1, 1),
    (N'2095', N'HCM-CH 173 Nguyễn Gia Trí', N'TP. Hồ Chí Minh', NULL, '2022-07-16', N'Pl.2095@phuclong.masangroup.com', 3, 1),
    (N'2096', N'LAN - CH 38 Hùng Vương', N'T. Long An', NULL, '2022-07-30', N'Pl.2096@phuclong.masangroup.com', 4, 1),
    (N'2097', N'HCM - CH 33 Nguyễn Văn Bảo', N'TP. Hồ Chí Minh', NULL, '2022-08-03', N'Pl.2097@phuclong.masangroup.com', 5, 1),
    (N'2098', N'VTU - CH 76 Trần Hưng Đạo', N'T. Bà Rịa - Vũng Tàu', NULL, '2022-07-22', N'Pl.2098@phuclong.masangroup.com', 3, 1),
    (N'2099', N'HCM - CH 190 Lê Văn Thọ', N'TP. Hồ Chí Minh', NULL, '2022-09-02', N'Pl.2099@phuclong.masangroup.com', 1, 1),
    (N'2100', N'HCM - CH 479 Kinh Dương Vương', N'TP. Hồ Chí Minh', NULL, '2022-09-02', N'Pl.2100@phuclong.masangroup.com', 11, 1),
    (N'2101', N'HPG - 200 Văn Cao', N'TP. Hải Phòng', NULL, '2022-08-26', N'Pl.2101@phuclong.masangroup.com', 23, 1),
    (N'2102', N'BDH - CH Nguyễn Thiếp', N'T. Bình Định', NULL, '2022-09-02', N'Pl.2102@phuclong.masangroup.com', 17, 1),
    (N'2103', N'HNI - 1B Nguyễn Hữu Huân', N'TP. Hà Nội', NULL, '2022-08-26', N'Pl.2103@phuclong.masangroup.com', 6, 1),
    (N'2104', N'BDG - CH Biconsi Tower', N'T. Bình Dương', NULL, '2022-09-23', N'Pl.2104@phuclong.masangroup.com', 9, 1),
    (N'2105', N'HCM - CH 1213 đường 3 tháng 2', N'TP. Hồ Chí Minh', NULL, '2022-09-29', N'Pl.2105@phuclong.masangroup.com', 16, 1),
    (N'2106', N'TGG - CH 12A1 Nguyễn Trãi', N'T. Tiền Giang', NULL, '2022-09-09', N'Pl.2106@phuclong.masangroup.com', 4, 1),
    (N'2107', N'HNI - 387 Trương Định', N'TP. Hà Nội', NULL, '2022-10-21', N'Pl.2107@phuclong.masangroup.com', 21, 1),
    (N'2108', N'DNI - CH 232 Nguyễn Ái Quốc', N'T. Đồng Nai', NULL, '2022-09-30', N'Pl.2108@phuclong.masangroup.com', 9, 1),
    (N'2109', N'QNH - 36A Trần Hưng Đạo', N'T. Quảng Ninh', NULL, '2022-11-18', N'Pl.2109@phuclong.masangroup.com', 21, 1),
    (N'2110', N'DLK - 118 Lý Thường Kiệt', N'T. Dak Lak', NULL, '2022-10-10', N'Pl.2110@phuclong.masangroup.com', 17, 1),
    (N'2111', N'DLK - 6 Ngô Quyền', N'T. Dak Lak', NULL, '2022-10-30', N'Pl.2111@phuclong.masangroup.com', 17, 1),
    (N'2113', N'VTU - CH 111 Thùy Vân', N'T. Bà Rịa - Vũng Tàu', NULL, '2022-10-28', N'Pl.2113@phuclong.masangroup.com', 3, 1),
    (N'2114', N'HNI - Aeon Long Biên', N'TP. Hà Nội', NULL, '2023-03-18', N'Pl.2114@phuclong.masangroup.com', 6, 1),
    (N'2115', N'KHA - 21 Ngô Gia Tự', N'T. Khánh Hòa', NULL, '2022-10-21', N'Pl.2115@phuclong.masangroup.com', 17, 1),
    (N'2116', N'DNG - 511 Trần Hưng Đạo', N'TP. Đà Nẵng', NULL, '2022-10-28', N'Pl.2116@phuclong.masangroup.com', 22, 1),
    (N'2117', N'HPG - 83 Trần Phú', N'TP. Hải Phòng', NULL, '2022-12-22', N'Pl.2117@phuclong.masangroup.com', 23, 1),
    (N'2118', N'NAN - Vinh Center', N'T. Nghệ An', NULL, '2022-10-27', N'Pl.2118@phuclong.masangroup.com', 21, 1),
    (N'2119', N'HCM - Hutech Q9', N'TP. Hồ Chí Minh', NULL, '2022-10-31', N'Pl.2119@phuclong.masangroup.com', 8, 1),
    (N'2120', N'QBH - Tuấn Việt Center', N'T. Quảng Bình', NULL, '2022-10-31', N'Pl.2120@phuclong.masangroup.com', 22, 1),
    (N'2121', N'BNH - 258 Nguyễn Gia Thiều', N'T. Bắc Ninh', NULL, '2022-12-31', N'Pl.2121@phuclong.masangroup.com', 20, 1),
    (N'2122', N'HCM - Lotte Tân Bình', N'TP. Hồ Chí Minh', NULL, '2022-10-31', N'Pl.2122@phuclong.masangroup.com', 5, 1),
    (N'2123', N'DNI - 230 Phan Trung', N'T. Đồng Nai', NULL, '2022-11-11', N'Pl.2123@phuclong.masangroup.com', 9, 1),
    (N'2124', N'HPG - Aeon Mall Hải Phòng', N'TP. Hải Phòng', NULL, '2023-01-12', N'Pl.2124@phuclong.masangroup.com', 23, 1),
    (N'2126', N'HYN - Eco Park', N'T. Hưng Yên', NULL, '2022-12-30', N'Pl.2126@phuclong.masangroup.com', 6, 1),
    (N'2127', N'HCM - 514A Lê Trọng Tấn', N'TP. Hồ Chí Minh', NULL, '2022-12-06', N'Pl.2127@phuclong.masangroup.com', 11, 1),
    (N'2130', N'BTE - Sense Bến Tre', N'T. Bến Tre', NULL, '2022-12-24', N'Pl.2130@phuclong.masangroup.com', 4, 1),
    (N'2131', N'CTO - Sense Cần Thơ', N'TP. Cần Thơ', NULL, '2022-12-24', N'Pl.2131@phuclong.masangroup.com', 4, 1),
    (N'2132', N'HCM - Coopmart Phan Văn Hớn', N'TP. Hồ Chí Minh', NULL, '2022-12-19', N'Pl.2132@phuclong.masangroup.com', 1, 1),
    (N'2133', N'HNI - Vincom Royal City', N'TP. Hà Nội', NULL, '2022-12-24', N'Pl.2133@phuclong.masangroup.com', 21, 1),
    (N'2134', N'HNI - Vincom Skylake', N'TP. Hà Nội', NULL, '2022-12-29', N'Pl.2134@phuclong.masangroup.com', 20, 1),
    (N'2135', N'HCM - Thiso mall', N'TP. Hồ Chí Minh', NULL, '2022-12-20', N'Pl.2135@phuclong.masangroup.com', 7, 1),
    (N'2136', N'HCM - Saigon Pearl', N'TP. Hồ Chí Minh', NULL, '2022-12-23', N'Pl.2136@phuclong.masangroup.com', 3, 1),
    (N'2137', N'HCM - 1A Nguyễn Văn Thủ', N'TP. Hồ Chí Minh', NULL, '2022-12-22', N'Pl.2137@phuclong.masangroup.com', 15, 1),
    (N'2138', N'HCM - 778 Điện Biên Phủ', N'TP. Hồ Chí Minh', NULL, '2023-03-09', N'Pl.2138@phuclong.masangroup.com', 12, 1),
    (N'2139', N'HCM - Vinhomes Grand Park', N'TP. Hồ Chí Minh', NULL, '2023-04-19', N'Pl.2139@phuclong.masangroup.com', 8, 1),
    (N'2140', N'HCM - Đoàn Như Hài', N'TP. Hồ Chí Minh', NULL, '2023-04-28', N'Pl.2140@phuclong.masangroup.com', 16, 1),
    (N'2141', N'HCM - 734 Kha Vạn Cân', N'TP. Hồ Chí Minh', NULL, '2023-04-25', N'Pl.2141@phuclong.masangroup.com', 8, 1),
    (N'2142', N'HCM - Techcombank Lê Duẩn', N'TP. Hồ Chí Minh', NULL, '2023-03-27', N'Pl.2142@phuclong.masangroup.com', 13, 1),
    (N'2143', N'HNI - Techcombank Quang Trung', N'TP. Hà Nội', NULL, '2023-03-27', N'Pl.2143@phuclong.masangroup.com', 6, 1),
    (N'2144', N'HCM - 875 CMT8', N'TP. Hồ Chí Minh', NULL, '2023-05-25', N'Pl.2144@phuclong.masangroup.com', 5, 1),
    (N'2145', N'HCM - Nguyễn Sơn', N'TP. Hồ Chí Minh', NULL, '2023-05-28', N'Pl.2145@phuclong.masangroup.com', 11, 1),
    (N'2146', N'HCM - Phạm Văn Chiêu', N'TP. Hồ Chí Minh', NULL, '2023-05-31', N'Pl.2146@phuclong.masangroup.com', 1, 1),
    (N'2147', N'HNI - Techcombank Trần Duy Hưng', N'TP. Hà Nội', NULL, '2023-05-31', N'Pl.2147@phuclong.masangroup.com', 20, 1),
    (N'2148', N'HCM - Lê Văn Việt', N'TP. Hồ Chí Minh', NULL, '2023-06-29', N'Pl.2148@phuclong.masangroup.com', 8, 1),
    (N'2149', N'HCM - Cống Quỳnh', N'TP. Hồ Chí Minh', NULL, '2023-06-24', N'Pl.2149@phuclong.masangroup.com', 15, 1),
    (N'2150', N'HCM - Cao Thắng', N'TP. Hồ Chí Minh', NULL, '2023-06-30', N'Pl.2150@phuclong.masangroup.com', 14, 1),
    (N'2151', N'HCM - 231 Lê Văn Sỹ', N'TP. Hồ Chí Minh', NULL, '2023-06-28', N'Pl.2151@phuclong.masangroup.com', 14, 1),
    (N'2152', N'HCM - Nguyễn Ảnh Thủ', N'TP. Hồ Chí Minh', NULL, '2023-08-28', N'Pl.2152@phuclong.masangroup.com', 1, 1),
    (N'2153', N'HCM - Nguyễn Thị Thập', N'TP. Hồ Chí Minh', NULL, '2023-07-28', N'Pl.2153@phuclong.masangroup.com', 13, 1),
    (N'2154', N'HCM - Võ Văn Ngân', N'TP. Hồ Chí Minh', NULL, '2023-08-01', N'Pl.2154@phuclong.masangroup.com', 8, 1),
    (N'2155', N'HCM - Hoàng Hoa Thám', N'TP. Hồ Chí Minh', NULL, '2023-08-29', N'Pl.2155@phuclong.masangroup.com', 5, 1),
    (N'2156', N'HCM - 481 Phan Văn Trị', N'TP. Hồ Chí Minh', NULL, '2023-08-23', N'Pl.2156@phuclong.masangroup.com', 5, 1),
    (N'2157', N'HCM - 254 Nguyễn Trãi', N'TP. Hồ Chí Minh', NULL, '2023-11-09', N'Pl.2157@phuclong.masangroup.com', 12, 1),
    (N'2158', N'HCM - Nguyễn Duy Trinh', N'TP. Hồ Chí Minh', NULL, '2023-10-06', N'Pl.2158@phuclong.masangroup.com', 7, 1),
    (N'2159', N'HCM - Nguyễn Công Trứ', N'TP. Hồ Chí Minh', NULL, '2023-10-27', N'Pl.2159@phuclong.masangroup.com', 13, 1),
    (N'2160', N'HCM - Nguyễn Xí', N'TP. Hồ Chí Minh', NULL, '2023-10-30', N'Pl.2160@phuclong.masangroup.com', 3, 1),
    (N'2161', N'DNI - 1335 Nguyễn Ái Quốc', N'T. Đồng Nai', NULL, '2023-11-20', N'Pl.2161@phuclong.masangroup.com', 9, 1),
    (N'2162', N'HCM - Emart Phan Huy Ích', N'TP. Hồ Chí Minh', NULL, '2023-12-04', N'Pl.2162@phuclong.masangroup.com', 1, 1),
    (N'2163', N'HCM - Nguyễn Đức Cảnh', N'TP. Hồ Chí Minh', NULL, '2024-01-24', N'Pl.2163@phuclong.masangroup.com', 13, 1),
    (N'2164', N'HNI - Time City', N'TP. Hà Nội', NULL, '2024-02-28', N'Pl.2164@phuclong.masangroup.com', 23, 1),
    (N'2165', N'HNI - Viet Tower', N'TP. Hà Nội', NULL, '2024-03-25', N'Pl.2165@phuclong.masangroup.com', 23, 1),
    (N'2166', N'HCM - Hai Bà Trưng', N'TP. Hồ Chí Minh', NULL, '2024-03-29', N'Pl.2166@phuclong.masangroup.com', 14, 1),
    (N'2167', N'VTU - Lê Hồng Phong', N'T. Bà Rịa - Vũng Tàu', NULL, '2024-04-20', N'Pl.2167@phuclong.masangroup.com', 3, 1),
    (N'2169', N'HCM - Xô Viết Nghệ Tĩnh', N'TP. Hồ Chí Minh', NULL, '2024-04-26', N'Pl.2169@phuclong.masangroup.com', 15, 1),
    (N'2170', N'BTN - Tôn Đức Thắng', N'T. Bình Thuận', NULL, '2024-04-24', N'Pl.2170@phuclong.masangroup.com', 17, 1),
    (N'2171', N'HCM - Saigon Center Office Tower', N'TP. Hồ Chí Minh', NULL, '2024-05-09', N'Pl.2171@phuclong.masangroup.com', 18, 1),
    (N'2172', N'HCM - Vincom Mega Mall Grand Park', N'TP. Hồ Chí Minh', NULL, '2024-06-01', N'Pl.2172@phuclong.masangroup.com', 8, 1),
    (N'2173', N'TTH - Aeonmall Huế', N'T. Thừa Thiên Huế', NULL, '2024-09-16', N'Pl.2173@phuclong.masangroup.com', 22, 1),
    (N'2174', N'VTU - KNG Mall', N'T. Bà Rịa - Vũng Tàu', NULL, '2024-06-30', N'Pl.2174@phuclong.masangroup.com', 3, 1),
    (N'2175', N'KHA - 26 Thái Nguyên', N'T. Khánh Hòa', NULL, '2024-07-17', N'Pl.2175@phuclong.masangroup.com', 17, 1),
    (N'2176', N'DNG - Xô Viết Nghệ Tĩnh', N'TP. Đà Nẵng', NULL, '2024-07-31', N'Pl.2176@phuclong.masangroup.com', 22, 1),
    (N'2177', N'DNI - Lê Duẩn', N'T. Đồng Nai', NULL, '2024-08-01', N'Pl.2177@phuclong.masangroup.com', 3, 1),
    (N'2178', N'QNH - Vincom Hạ Long', N'T. Quảng Ninh', NULL, '2024-07-22', N'Pl.2178@phuclong.masangroup.com', 21, 1),
    (N'2179', N'HNI - Vinhomes Gardenia', N'TP. Hà Nội', NULL, '2024-08-31', N'Pl.2179@phuclong.masangroup.com', 20, 1),
    (N'2180', N'HCM - Lexington', N'TP. Hồ Chí Minh', NULL, '2024-09-29', N'Pl.2180@phuclong.masangroup.com', 7, 1),
    (N'2181', N'HYN - Sol Forest', N'T. Hưng Yên', NULL, '2024-08-17', N'Pl.2181@phuclong.masangroup.com', 6, 1),
    (N'2182', N'DNI - Đồng Khởi', N'T. Đồng Nai', NULL, '2024-08-22', N'Pl.2182@phuclong.masangroup.com', 9, 1),
    (N'2183', N'KHA - Dã Tượng', N'T. Khánh Hòa', NULL, '2024-09-30', N'Pl.2183@phuclong.masangroup.com', 17, 1),
    (N'2184', N'HCM - Celadon', N'TP. Hồ Chí Minh', NULL, '2024-08-14', N'Pl.2184@phuclong.masangroup.com', 18, 1),
    (N'2185', N'HCM - Lumiere', N'TP. Hồ Chí Minh', NULL, '2024-09-25', N'Pl.2185@phuclong.masangroup.com', 7, 1),
    (N'2186', N'HNI - Trần Quốc Hoàn', N'TP. Hà Nội', NULL, '2024-09-30', N'Pl.2186@phuclong.masangroup.com', 23, 1),
    (N'2187', N'HCM - Parc Mall', N'TP. Hồ Chí Minh', NULL, '2024-09-04', N'Pl.2187@phuclong.masangroup.com', 12, 1),
    (N'2188', N'HCM - Lãnh Binh Thăng', N'TP. Hồ Chí Minh', NULL, '2025-12-15', N'Pl.2188@phuclong.masangroup.com', 16, 1),
    (N'2189', N'HCM - 457A Trần Hưng Đạo', N'TP. Hồ Chí Minh', NULL, '2024-11-12', N'Pl.2189@phuclong.masangroup.com', 18, 1),
    (N'2190', N'HCM - 202 Trương Công Định', N'TP. Hồ Chí Minh', NULL, '2024-11-20', N'Pl.2190@phuclong.masangroup.com', 18, 1),
    (N'2191', N'CTO - Lotte Cần Thơ', N'TP. Cần Thơ', NULL, '2024-10-20', N'Pl.2191@phuclong.masangroup.com', 4, 1),
    (N'2192', N'HCM - Central Premium', N'TP. Hồ Chí Minh', NULL, '2024-11-15', N'Pl.2192@phuclong.masangroup.com', 12, 1),
    (N'2193', N'HCM - Hoàng Diệu', N'TP. Hồ Chí Minh', NULL, '2024-11-28', N'Pl.2193@phuclong.masangroup.com', 16, 1),
    (N'2194', N'HCM - Lê Thị Hà', N'TP. Hồ Chí Minh', NULL, '2024-12-12', N'Pl.2194@phuclong.masangroup.com', 1, 1),
    (N'2195', N'LDG - Bùi Thị Xuân', N'T. Lâm Đồng', NULL, '2025-01-11', N'Pl.2195@phuclong.masangroup.com', 17, 1),
    (N'2196', N'HCM - AEON Tân Phú', N'TP. Hồ Chí Minh', NULL, '2024-12-20', N'Pl.2196@phuclong.masangroup.com', 18, 1),
    (N'2197', N'HCM - Satra Võ Văn Kiệt', N'TP. Hồ Chí Minh', NULL, '2024-12-20', N'Pl.2197@phuclong.masangroup.com', 16, 1),
    (N'2198', N'BDH - Nguyễn Tất Thành', N'T. Bình Định', NULL, '2024-12-31', N'Pl.2198@phuclong.masangroup.com', 17, 1),
    (N'2199', N'HCM - 285 CMT8', N'TP. Hồ Chí Minh', NULL, '2025-08-08', N'Pl.2199@phuclong.masangroup.com', 12, 1),
    (N'2200', N'NAN - Lotte Vinh', N'T. Nghệ An', NULL, '2025-03-30', N'Pl.2200@phuclong.masangroup.com', 21, 1),
    (N'2201', N'HCM - The Grace', N'TP. Hồ Chí Minh', NULL, '2025-03-28', N'Pl.2201@phuclong.masangroup.com', 13, 1),
    (N'2202', N'HNI - Green Diamond', N'TP. Hà Nội', NULL, '2025-06-11', N'Pl.2202@phuclong.masangroup.com', 21, 1),
    (N'2203', N'HCM - Phạm Ngọc Thạch', N'TP. Hồ Chí Minh', NULL, '2025-09-12', N'Pl.2203@phuclong.masangroup.com', 14, 1),
    (N'2204', N'TTH - Công viên Kim Đồng', N'T. Thừa Thiên Huế', NULL, '2025-07-24', N'Pl.2204@phuclong.masangroup.com', 22, 1),
    (N'2205', N'BDG - 153 Đường 30 Tháng 4', N'T. Bình Dương', NULL, '2025-09-10', N'Pl.2205@phuclong.masangroup.com', 9, 1),
    (N'2206', N'HNI - Hoàng Đạo Thúy', N'TP. Hà Nội', NULL, '2025-08-28', N'Pl.2206@phuclong.masangroup.com', 20, 1),
    (N'2207', N'HYN - Vincom Ocean City', N'T. Hưng Yên', NULL, '2025-08-22', N'Pl.2207@phuclong.masangroup.com', 6, 1),
    (N'2208', N'KGG - Sân bay Phú Quốc', N'T. An Giang', NULL, '2025-11-20', N'Pl.2208@phuclong.masangroup.com', 11, 1),
    (N'2209', N'HNI - Go Thăng Long', N'TP. Hà Nội', NULL, '2025-11-11', N'Pl.2209@phuclong.masangroup.com', 20, 1),
    (N'2210', N'HNI - Hà Nội Centre', N'TP. Hà Nội', NULL, '2025-12-27', N'Pl.2210@phuclong.masangroup.com', 23, 1),
    (N'2211', N'HNI - The Manor', N'TP. Hà Nội', NULL, '2025-10-10', N'Pl.2211@phuclong.masangroup.com', 23, 1),
    (N'2212', N'HNI - Vincom Trần Duy Hưng', N'TP. Hà Nội', NULL, '2025-09-10', N'Pl.2212@phuclong.masangroup.com', 20, 1),
    (N'2213', N'BDG - Bcons Bình Dương', N'T. Bình Dương', NULL, '2025-11-14', N'Pl.2213@phuclong.masangroup.com', 9, 1),
    (N'2216', N'BDG - Midori', N'T. Bình Dương', NULL, '2025-11-21', N'Pl.2216@phuclong.masangroup.com', 9, 1),
    (N'2217', N'DNG - Mega Market', N'TP. Đà Nẵng', NULL, '2025-11-17', N'Pl.2217@phuclong.masangroup.com', 22, 1),
    (N'2218', N'HNI - Taisei', N'TP. Hà Nội', NULL, '2025-12-29', N'Pl.2218@phuclong.masangroup.com', 20, 1),
    (N'2219', N'VTU - Go Bà Rịa', N'T. Bà Rịa - Vũng Tàu', NULL, '2025-12-10', N'Pl.2219@phuclong.masangroup.com', 3, 1),
    (N'2220', N'HNI - Nguyễn Đình Thi', N'TP. Hà Nội', NULL, '2025-12-24', N'Pl.2220@phuclong.masangroup.com', 23, 1),
    (N'2221', N'HNI - Rox Centre', N'TP. Hà Nội', NULL, '2026-01-30', N'Pl.2221@phuclong.masangroup.com', 20, 1),
    (N'2222', N'TGG - Go Mỹ Tho', N'T. Tiền Giang', NULL, '2025-12-12', N'Pl.2222@phuclong.masangroup.com', 4, 1),
    (N'2223', N'KHA - Go Nha Trang', N'T. Khánh Hòa', NULL, '2026-01-24', N'Pl.2223@phuclong.masangroup.com', 17, 1),
    (N'2224', N'BDG - Nguyễn An Ninh', N'TP. Hồ Chí Minh', NULL, '2026-02-11', N'Pl.2224@phuclong.masangroup.com', 9, 1),
    (N'2225', N'HNI - Giao Lưu Urban', N'TP. Hà Nội', NULL, '2026-02-12', N'Pl.2225@phuclong.masangroup.com', 23, 1),
    (N'2226', N'HNI - Tasco Mall', NULL, NULL, '2026-04-24', N'Pl.2226@phuclong.masangroup.com', 6, 1),
    (N'2231', N'KGG - Hùng Vương, Phú Quốc', NULL, NULL, '2026-04-25', N'Pl.2231@phuclong.masangroup.com', 11, 1),
    (N'2236', N'HCM - Waterbus Thủ Thiêm', N'TP. Hồ Chí Minh', NULL, '2026-04-29', N'Pl.2236@phuclong.masangroup.com', 7, 1),
    (N'2234', N'HNI - Phan Đình Phùng', N'Hà Nội', NULL, '2026-05-19', N'Pl.2234@phuclong.masangroup.com', 6, 1),
    (N'2233', N'KGG - Sunworld Phú Quốc', N'An Giang', NULL, '2026-05-28', N'Pl.2233@phuclong.masangroup.com', 11, 1),
    (N'2242', N'BDG - Vincom Dĩ An', N'TP. Hồ Chí Minh', NULL, '2026-05-29', N'Pl.2242@phuclong.masangroup.com', 9, 1),
    (N'2237', N'DNG - 111 Trần Hưng Đạo', N'Đà Nẵng', NULL, '2026-05-31', N'Pl.2237@phuclong.masangroup.com', 22, 1),
    (N'2239', N'HCM - Opera Metropole Thủ Thiêm', N'TP. Hồ Chí Minh', NULL, '2026-06-10', N'Pl.2239@phuclong.masangroup.com', 7, 1),
    (N'2243', N'HCM - Vincom Thảo Điền', N'TP. Hồ Chí Minh', NULL, '2026-06-24', N'Pl.2243@phuclong.masangroup.com', 7, 1),
    (N'2245', N'HNI - Vincom  Vinsmart City', N'Thành phố Hà Nội', NULL, '2026-06-17', N'Pl.2245@phuclong.masangroup.com', 21, 1),
    (N'2241', N'HNI - Miami Vinhomes', N'Thành phố Hà Nội', NULL, '2026-06-18', N'Pl.2241@phuclong.masangroup.com', 21, 1),
    (N'2248', N'HCM - Phạm Văn Nghị', N'TP. Hồ Chí Minh', NULL, '2026-06-19', N'Pl.2248@phuclong.masangroup.com', 13, 1),
    (N'2246', N'VTU - 90 Hạ Long', N'TP. Vũng Tàu', NULL, '2026-06-20', N'Pl.2246@phuclong.masangroup.com', 3, 1),
    (N'2251', N'HPG - Vincom Lê Thánh Tông', N'TP. Hải Phòng', NULL, '2026-06-25', N'Pl.2251@phuclong.masangroup.com', 23, 1),
    (N'2238', N'HCM - 97 Hai Bà Trưng', N'TP. Hồ Chí Minh', NULL, '2026-06-29', N'Pl.2238@phuclong.masangroup.com', 18, 1),
    (N'2247', N'HNI – Nội Bài Domestic Ariport (T1)', N'Hà Nội', NULL, '2026-07-13', N'Pl.2247@phuclong.masangroup.com', 20, 1),
    (N'2244', N'HCM - Đại học UEF CS2', N'TP. Hồ Chí Minh', NULL, '2026-07-15', N'Pl.2244@phuclong.masangroup.com', 15, 1),
    (N'2240', N'HNI - THE MARC 88', N'Hà Nội', NULL, '2026-07-22', N'Pl.2240@phuclong.masangroup.com', 20, 1),
    (N'2253', N'QNH - Monbay Hạ Long', NULL, NULL, '2026-07-23', N'Pl.2253@phuclong.masangroup.com', 21, 1),
    (N'2254', N'BTN - Trần Hưng Đạo', N'Lâm Đồng', NULL, '2026-07-23', N'Pl.2254@phuclong.masangroup.com', 17, 1),
    (N'2249', N'HCM - Nguyễn Thị Nhung', N'Hồ Chí Minh', NULL, '2026-07-24', N'Pl.2249@phuclong.masangroup.com', 8, 1),
    (N'2258', N'HCM - Beverly Solari', N'Hồ Chí Minh', NULL, '2026-07-30', N'Pl.2258@phuclong.masangroup.com', 8, 1),
    (N'2260', N'HCM - Tạ Hiện Q2', N'Hồ Chí Minh', NULL, '2026-07-30', N'Pl.2260@phuclong.masangroup.com', 7, 1),
    (N'2261', N'HCM - Riverside Q7', N'Hồ Chí Minh', NULL, '2026-07-31', N'Pl.2261@phuclong.masangroup.com', 13, 1),
    (N'2255', N'DNG - Nguyễn Văn Thoại', N'Đà Nẵng', NULL, '2026-08-07', N'Pl.2255@phuclong.masangroup.com', 22, 1),
    (N'2256', N'HCM - Bình Phú', N'Thành Phố Hồ Chí Minh', NULL, '2026-08-10', N'Pl.2256@phuclong.masangroup.com', 16, 1),
    (N'2252', N'KGG - Ba Tháng Hai', NULL, NULL, '2026-08-13', N'Pl.2252@phuclong.masangroup.com', 4, 1),
    (N'2257', N'AGG - Vincom Long Xuyên', NULL, NULL, '2026-08-14', N'Pl.2257@phuclong.masangroup.com', 4, 1),
    (N'2266', N'KHA - Panorama', NULL, NULL, '2026-08-23', N'Pl.2266@phuclong.masangroup.com', 17, 1),
    (N'2259', N'HNI - Bưu Điện Hà Nội', N'Hà Nội', NULL, '2026-08-27', N'Pl.2259@phuclong.masangroup.com', 6, 1),
    (N'2262', N'DNG - VNPT Đà Nẵng', NULL, NULL, '2026-08-29', N'Pl.2262@phuclong.masangroup.com', 22, 1),
    (N'2265', N'HCM - Phan Đăng Lưu', N'TP. Hồ Chí Minh', NULL, '2026-08-30', N'Pl.2265@phuclong.masangroup.com', 14, 1),
    (N'2263', N'LDG - Nguyễn Chí Thanh', NULL, NULL, '2026-08-31', N'Pl.2263@phuclong.masangroup.com', 17, 1),
    (N'2267', N'HCM - Huỳnh Tấn Phát', N'TP. Hồ Chí Minh', NULL, '2026-08-31', N'Pl.2267@phuclong.masangroup.com', 13, 1),
    (N'2264', N'AGG - Hai Bà Trưng', NULL, NULL, '2026-08-31', N'Pl.2264@phuclong.masangroup.com', 4, 1),
    (N'4335', N'The West Cầu Giấy', NULL, NULL, '2026-09-07', N'Pl.4335@phuclong.masangroup.com', 20, 1),
    (N'4334', N'Sacom Chip Sáng Khu CN Cao Q9', NULL, NULL, '2026-09-18', N'Pl.4334@phuclong.masangroup.com', 8, 1),
    (N'2271', N'Artex Building', NULL, NULL, '2026-09-27', N'Pl.2271@phuclong.masangroup.com', 20, 1),
    (N'2269', N'197 Trung Sơn Bình Chánh', NULL, NULL, '2026-09-28', N'Pl.2269@phuclong.masangroup.com', 12, 1),
    (N'2215', N'HCM - SB Tân Sơn Nhất', N'TP. Hồ Chí Minh', NULL, '2026-09-29', N'Pl.2215@phuclong.masangroup.com', 5, 1),
    (N'2268', N'107 Nguyễn Văn Tạo - Nhà Bè', N'TP. Hồ Chí Minh', NULL, '2026-09-30', N'Pl.2268@phuclong.masangroup.com', 13, 1),
    (N'2273', N'Nguyen Huu Tho Q7/ Ngô Thị Bì Q7', NULL, NULL, '2026-09-30', N'Pl.2273@phuclong.masangroup.com', 13, 1),
    (N'2230', N'THA - Aeon Mall Thanh Hóa', NULL, NULL, '2026-10-15', N'Pl.2230@phuclong.masangroup.com', 20, 1),
    (N'2272', N'Số 2-4 Cầu Đất Hải Phòng', NULL, NULL, '2026-10-06', N'Pl.2272@phuclong.masangroup.com', NULL, 1),
    (N'2270', N'572 3 tháng 2 quận 10', NULL, NULL, '2026-10-29', N'Pl.2270@phuclong.masangroup.com', NULL, 1),
    (N'3131', N'HCM-PLVM+ 50-52 50A, P. Tân Tạo, Q.', N'TP. Hồ Chí Minh', NULL, '2022-10-27', N'Pl.3131@phuclong.masangroup.com', 11, 1),
    (N'3162', N'HCM-PLVM+ 206 Đình Phong Phú, P.TNP B,', N'TP. Hồ Chí Minh', NULL, '2022-12-17', N'Pl.3162@phuclong.masangroup.com', 8, 1),
    (N'3164', N'HCM-PLVM+ 81 số 2, KP6, P. Hiệp Bình', N'TP. Hồ Chí Minh', NULL, '2022-10-25', N'Pl.3164@phuclong.masangroup.com', 8, 1),
    (N'3177', N'HCM-PLVM+ 84 Gò Ô Môi, P.Phú Thuận,', N'TP. Hồ Chí Minh', NULL, '2022-10-30', N'Pl.3177@phuclong.masangroup.com', 13, 1),
    (N'3204', N'VM+ HCM 96 Lâm Văn Bền', N'TP. Hồ Chí Minh', NULL, '2021-06-30', N'Pl.3204@phuclong.masangroup.com', 13, 1),
    (N'3209', N'HCM-PLVM+ 196 Mã Lò, KP 6, P.Bình Trị', N'TP. Hồ Chí Minh', NULL, '2022-10-24', N'Pl.3209@phuclong.masangroup.com', 11, 1),
    (N'3213', N'HCM-PLVM+ New City 17M.Chí Thọ-P.AP-', N'TP. Hồ Chí Minh', NULL, '2022-08-20', N'Pl.3213@phuclong.masangroup.com', 7, 1),
    (N'3215', N'HCM-PLVM+ The Sun AVENUA 28MCT', N'TP. Hồ Chí Minh', NULL, '2022-08-20', N'Pl.3215@phuclong.masangroup.com', 7, 1),
    (N'3237', N'HCM-PLVM+ 237 Nguyễn Văn Hưởng', N'TP. Hồ Chí Minh', NULL, '2022-12-30', N'Pl.3237@phuclong.masangroup.com', 7, 1),
    (N'3251', N'HCM-PLVM+ 476 Phan Xích Long - P3 - Q.', N'TP. Hồ Chí Minh', NULL, '2022-10-30', N'Pl.3251@phuclong.masangroup.com', 14, 1),
    (N'3253', N'HCM-PLVM+ 85A Quốc Lộ 13', N'TP. Hồ Chí Minh', NULL, '2022-12-07', N'Pl.3253@phuclong.masangroup.com', 8, 1),
    (N'3267', N'VM+ HCM 950-950A Tạ Quang Bửu', N'TP. Hồ Chí Minh', NULL, '2021-06-15', N'Pl.3267@phuclong.masangroup.com', 12, 1),
    (N'3410', N'HCM PLVM+ The Era Town', N'TP. Hồ Chí Minh', NULL, '2022-10-31', N'Pl.3410@phuclong.masangroup.com', 13, 1),
    (N'3417', N'WIN HCM 66/10A Bình Thành,', N'TP. Hồ Chí Minh', NULL, '2023-03-01', N'Pl.3417@phuclong.masangroup.com', 11, 1),
    (N'3506', N'BDG PLVM+ 116-118 đường số 9', N'T. Bình Dương', NULL, '2022-12-30', N'Pl.3506@phuclong.masangroup.com', 9, 1),
    (N'3507', N'BDG PLVM+ 06 Đoàn Thị Kìa', N'T. Bình Dương', NULL, '2022-12-25', N'Pl.3507@phuclong.masangroup.com', 9, 1),
    (N'3769', N'CM PLVM+ 2 Thăng Long', N'TP. Hồ Chí Minh', NULL, '2022-12-23', N'Pl.3769@phuclong.masangroup.com', 5, 1),
    (N'4274', N'HNI VM+ SHA-110, Tòa A2 KĐT Ciputra', N'TP. Hà Nội', NULL, '2022-08-20', N'Pl.4274@phuclong.masangroup.com', 23, 1),
    (N'4289', N'HCM WM+ SH21-22 CC ECO GREEN', N'TP. Hồ Chí Minh', NULL, '2022-10-14', N'Pl.4289@phuclong.masangroup.com', 13, 1)
) AS s (Code, Name, City, Concept, OpenDate, Email, AreaManagerId, IsActive)
ON t.Code = s.Code
WHEN MATCHED THEN UPDATE SET
    Name = s.Name, City = s.City, Concept = s.Concept, OpenDate = s.OpenDate,
    Email = s.Email, AreaManagerId = s.AreaManagerId, IsActive = s.IsActive
WHEN NOT MATCHED THEN INSERT (Code, Name, City, Concept, OpenDate, Email, AreaManagerId, IsActive)
VALUES (s.Code, s.Name, s.City, s.Concept, s.OpenDate, s.Email, s.AreaManagerId, s.IsActive);

PRINT 'Store org seed completed.';