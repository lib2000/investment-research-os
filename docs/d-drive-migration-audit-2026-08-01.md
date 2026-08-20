# D Drive Migration Audit

Date: 2026-08-01

## Active Workspace

- Workspace root: `D:\workspace`
- Investment Research OS: `D:\workspace\InvestmentJournalApp`
- OpenClaw: `D:\workspace\openclaw`
- The external drive must remain mounted as `D:`. Project scripts must stop when it is unavailable instead of falling back to a C-drive copy.

## Verified

- Investment Research OS scheduled tasks use the D-drive project root.
- Scheduled task command lines do not contain a retired project root or a plaintext development token.
- The research API is running from the D-drive virtual environment on port `8001`.
- The development port registry resolves every registered project root under `D:\workspace`.
- OpenClaw memory and heartbeat instructions point to the D-drive InvestmentJournalApp checkout.
- Sports analysis integration and investigation checkout Git pointers were repaired after the folder move.
- Active source, scripts, and operational documentation under `D:\workspace` no longer reference the retired C-drive project roots.

## Remaining Risks

- The current Codex desktop task may still show an old OneDrive working directory. Open future tasks from `D:\workspace`.
- C-drive project copies still exist under `C:\Projects` and `C:\Users\lib20\projects`. Treat them as cleanup candidates only after file and Git comparison; do not run services from them.
- Sports source-data defaults still refer to `C:\AI\자료실\국제 축구 경기 결과`. No matching D-drive data directory was found, so these paths were not changed automatically.
- OpenClaw strict bridge health is not green while the InvestmentJournalApp worktree is dirty, local `main` is ahead of upstream, and final completion-report hashes are missing. Runtime context checks unrelated to final Git completion remain healthy.
- Because `D:` is an external drive, an unplugged drive or changed drive letter will stop scheduled jobs. Keep a stable drive letter and reconnect the drive before sign-in automation runs.

## Cleanup Gate

Before deleting a C-drive copy:

1. Confirm the matching D-drive project exists.
2. Compare Git branch, commit, tracked changes, untracked files, and ignored runtime data.
3. Stop any process using the C-drive path.
4. Back up private runtime data that is not tracked by Git.
5. Delete only after explicit approval.

## C Drive Cleanup Completed

The user approved removal of the retired C-drive InvestmentJournalApp files on 2026-08-01.

- Removed the retired OneDrive project folder at `C:\Users\lib20\OneDrive\work\New project\InvestmentJournalApp`.
- Removed the old local investment source folder at `C:\AI\투자` after copying it to `D:\Backup\InvestmentJournalApp_C_cleanup_20260801\AI_투자`.
- Removed `C:\Users\lib20\Documents\Invest` after copying it to the same D-drive archive.
- Preserved unique files from the retired OneDrive research vault in `D:\Backup\InvestmentJournalApp_C_cleanup_20260801\OneDrive_research_vault`.
- Moved the live KIS configuration to `D:\workspace\KIS`, restricted its ACL, and left only a compatibility junction at `C:\Users\lib20\KIS` because the upstream trading client resolves `~/KIS/config`.
- Verified 67 moved files by SHA-256 with zero mismatches before deleting the C-drive originals.
- Removed six old Codex configuration backups and rollout summaries named for InvestmentJournalApp.
- Did not remove the separately imported brokerage statement under OneDrive because deleting it could also delete the cloud copy and it is not part of the retired project checkout.
