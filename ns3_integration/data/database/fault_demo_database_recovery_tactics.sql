-- RECOVERY TACTICS TABLE
INSERT INTO RecoveryTactics VALUES (1, 'Emergency_Reroute', 'Immediately reroute traffic through alternative paths', 30, 'medium', TRUE, 1);
INSERT INTO RecoveryTactics VALUES (2, 'Physical_Repair', 'Dispatch repair team for physical fiber restoration', 7200, 'low', FALSE, 2);
INSERT INTO RecoveryTactics VALUES (3, 'Redundant_Path_Activation', 'Activate pre-configured redundant fiber paths', 60, 'low', TRUE, 1);
INSERT INTO RecoveryTactics VALUES (4, 'Backup_Power_Switch', 'Switch to backup power source', 120, 'medium', TRUE, 3);
INSERT INTO RecoveryTactics VALUES (5, 'Load_Shedding', 'Reduce power consumption by shedding non-critical loads', 15, 'high', TRUE, 3);
INSERT INTO RecoveryTactics VALUES (6, 'Generator_Deployment', 'Deploy emergency generator', 1800, 'low', FALSE, 2);
INSERT INTO RecoveryTactics VALUES (7, 'Traffic_Load_Balance', 'Redistribute traffic across available links', 45, 'low', TRUE, 1);
INSERT INTO RecoveryTactics VALUES (8, 'QoS_Prioritization', 'Adjust QoS policies to prioritize critical traffic', 30, 'medium', TRUE, 4);
INSERT INTO RecoveryTactics VALUES (9, 'Node_Restart', 'Restart affected network node', 300, 'high', TRUE, 4);

