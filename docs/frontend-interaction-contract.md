# Frontend Interaction Contract

The workspace follows progressive disclosure: frequent work stays visible, contextual work stays within two actions, and maintenance or destructive operations live in labelled menus.

## Always available

- Create a conversation.
- Select a workspace or recent conversation.
- Switch between Chat and Code.
- Select and inspect tables, charts, scalar values, and execution logs in Results.
- Attach a file, select a model, and submit or stop a prompt.
- Open Settings and collapse or expand the sidebar.

## Contextual or secondary

- Schema and Conversation Tree live under Workspace tools when the sidebar is expanded and remain direct icon actions when collapsed.
- The result selector stays in the Results header; export, search, and other actions appear only when they apply to the selected result.
- Execution output related to a table, chart, or scalar remains available from the selected result without duplicating the rendered result.
- Terminal controls appear only while the terminal is open.
- New result indicators appear without stealing keyboard focus.

## Deeper or guarded

- Provider credentials and model administration live in Settings.
- Advanced generation controls remain collapsed by default.
- Destructive table and chart actions live in overflow menus and retain confirmation dialogs.
- Workspace deletion and database maintenance remain inside workspace management.

## Accessibility and responsive baseline

- All primary workflows are keyboard operable.
- Menus restore focus to their trigger.
- Dialogs trap focus and close with Escape when safe.
- At narrow widths, Work and Data use a single-pane switcher rather than compressing both panes.
- Motion respects `prefers-reduced-motion`.
- Supported minimum content width is 640px; smaller widths use compact controls and stacked Settings navigation.
