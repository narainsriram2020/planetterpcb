"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { LogOut, MoreHorizontal, Pencil, Shield, SquarePen, Trash2, UserX, X } from "lucide-react";
import type { Conversation } from "@/types/chat";
import { Logo } from "./Logo";
import styles from "./Sidebar.module.css";

export interface SidebarUser {
  name: string | null;
  email: string | null;
  avatarUrl: string | null;
}

interface SidebarProps {
  conversations: Conversation[];
  loading: boolean;
  activeId: string | null;
  user: SidebarUser;
  open: boolean; // mobile drawer
  onClose: () => void;
  onSelect: (id: string) => void;
  onNew: () => void;
  onRename: (id: string, title: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  onDeleteAll: () => Promise<void>;
  onDeleteAccount: () => Promise<void>;
  onSignOut: () => void;
}

const DAY = 24 * 60 * 60 * 1000;

function groupByDate(conversations: Conversation[]): [string, Conversation[]][] {
  const startOfToday = new Date().setHours(0, 0, 0, 0);
  const groups: Record<string, Conversation[]> = {};
  for (const c of conversations) {
    const t = new Date(c.updated_at).getTime();
    const label =
      t >= startOfToday ? "Today"
      : t >= startOfToday - DAY ? "Yesterday"
      : t >= startOfToday - 7 * DAY ? "Previous 7 days"
      : t >= startOfToday - 30 * DAY ? "Previous 30 days"
      : "Older";
    (groups[label] ??= []).push(c);
  }
  return ["Today", "Yesterday", "Previous 7 days", "Previous 30 days", "Older"]
    .filter((label) => groups[label])
    .map((label) => [label, groups[label]]);
}

/** Closes a popover when clicking outside it or pressing Escape. */
function useDismiss(open: boolean, close: () => void) {
  const ref = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    if (!open) return;
    const onPointer = (e: PointerEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) close();
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close();
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, close]);
  return ref;
}

function ConversationItem({
  conversation, active, onSelect, onRename, onDelete,
}: {
  conversation: Conversation;
  active: boolean;
  onSelect: () => void;
  onRename: (title: string) => Promise<void>;
  onDelete: () => Promise<void>;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(conversation.title);
  const closeMenu = () => {
    setMenuOpen(false);
    setConfirmDelete(false);
  };
  const menuRef = useDismiss(menuOpen, closeMenu);

  const saveTitle = async () => {
    const title = draft.trim();
    setEditing(false);
    if (title && title !== conversation.title) await onRename(title);
  };

  if (editing) {
    return (
      <li className={`${styles.item} ${styles.itemActive}`}>
        <input
          className={styles.renameInput}
          value={draft}
          autoFocus
          maxLength={80}
          aria-label="Chat title"
          onChange={(e) => setDraft(e.target.value)}
          onBlur={saveTitle}
          onKeyDown={(e) => {
            if (e.key === "Enter") saveTitle();
            if (e.key === "Escape") {
              setDraft(conversation.title);
              setEditing(false);
            }
          }}
        />
      </li>
    );
  }

  return (
    <li className={`${styles.item} ${active ? styles.itemActive : ""}`}>
      <button type="button" className={styles.itemButton} onClick={onSelect} title={conversation.title}>
        {conversation.title}
      </button>
      <div className={styles.itemMenuWrap} ref={menuRef}>
        <button
          type="button"
          className={styles.itemMore}
          aria-label={`Options for ${conversation.title}`}
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((o) => !o)}
        >
          <MoreHorizontal size={16} />
        </button>
        {menuOpen && (
          <div className={styles.menu} role="menu">
            <button type="button" role="menuitem" onClick={() => { closeMenu(); setDraft(conversation.title); setEditing(true); }}>
              <Pencil size={14} /> Rename
            </button>
            <button
              type="button"
              role="menuitem"
              className={styles.danger}
              onClick={async () => {
                if (!confirmDelete) return setConfirmDelete(true);
                closeMenu();
                await onDelete();
              }}
            >
              <Trash2 size={14} /> {confirmDelete ? "Click again to delete" : "Delete"}
            </button>
          </div>
        )}
      </div>
    </li>
  );
}

function AccountMenu({
  user, onSignOut, onDeleteAll, onDeleteAccount,
}: Pick<SidebarProps, "user" | "onSignOut" | "onDeleteAll" | "onDeleteAccount">) {
  const [open, setOpen] = useState(false);
  const [confirm, setConfirm] = useState<"all" | "account" | null>(null);
  const close = () => {
    setOpen(false);
    setConfirm(null);
  };
  const ref = useDismiss(open, close);
  const initial = (user.name || user.email || "?").trim().charAt(0).toUpperCase();

  return (
    <div className={styles.account} ref={ref}>
      {open && (
        <div className={`${styles.menu} ${styles.accountMenu}`} role="menu">
          <Link href="/privacy" role="menuitem" onClick={close}>
            <Shield size={14} /> Privacy
          </Link>
          <button
            type="button"
            role="menuitem"
            className={styles.danger}
            onClick={async () => {
              if (confirm !== "all") return setConfirm("all");
              close();
              await onDeleteAll();
            }}
          >
            <Trash2 size={14} /> {confirm === "all" ? "Click again: delete all chats" : "Delete all chats"}
          </button>
          <button
            type="button"
            role="menuitem"
            className={styles.danger}
            onClick={async () => {
              if (confirm !== "account") return setConfirm("account");
              close();
              await onDeleteAccount();
            }}
          >
            <UserX size={14} /> {confirm === "account" ? "Click again: delete account" : "Delete account"}
          </button>
          <div className={styles.menuDivider} />
          <button type="button" role="menuitem" onClick={() => { close(); onSignOut(); }}>
            <LogOut size={14} /> Sign out
          </button>
        </div>
      )}
      <button type="button" className={styles.accountButton} onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        {user.avatarUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img className={styles.avatar} src={user.avatarUrl} alt="" referrerPolicy="no-referrer" />
        ) : (
          <span className={styles.avatar}>{initial}</span>
        )}
        <span className={styles.accountText}>
          <span className={styles.accountName}>{user.name || user.email}</span>
          {user.name && user.email && <span className={styles.accountEmail}>{user.email}</span>}
        </span>
        <MoreHorizontal size={16} className={styles.accountMore} />
      </button>
    </div>
  );
}

export function Sidebar(props: SidebarProps) {
  const { conversations, loading, activeId, open, onClose, onSelect, onNew } = props;
  const groups = groupByDate(conversations);

  return (
    <>
      <div className={`${styles.backdrop} ${open ? styles.backdropOpen : ""}`} onClick={onClose} aria-hidden="true" />
      <aside className={`${styles.sidebar} ${open ? styles.sidebarOpen : ""}`} aria-label="Saved chats">
        <div className={styles.head}>
          <Logo />
          <button type="button" className={styles.close} onClick={onClose} aria-label="Close menu">
            <X size={18} />
          </button>
        </div>

        <button type="button" className={styles.newChat} onClick={onNew}>
          <SquarePen size={16} /> New chat
        </button>

        <nav className={styles.list}>
          {loading && conversations.length === 0 ? (
            <div className={styles.skeleton} aria-label="Loading chats">
              <span /><span /><span />
            </div>
          ) : conversations.length === 0 ? (
            <p className={styles.empty}>Your chats will show up here.</p>
          ) : (
            groups.map(([label, items]) => (
              <section key={label}>
                <h2 className={styles.groupLabel}>{label}</h2>
                <ul>
                  {items.map((c) => (
                    <ConversationItem
                      key={c.id}
                      conversation={c}
                      active={c.id === activeId}
                      onSelect={() => onSelect(c.id)}
                      onRename={(title) => props.onRename(c.id, title)}
                      onDelete={() => props.onDelete(c.id)}
                    />
                  ))}
                </ul>
              </section>
            ))
          )}
        </nav>

        <AccountMenu
          user={props.user}
          onSignOut={props.onSignOut}
          onDeleteAll={props.onDeleteAll}
          onDeleteAccount={props.onDeleteAccount}
        />
      </aside>
    </>
  );
}
