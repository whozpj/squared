import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Card, EmptyState, Field, Icon, Input, Modal, Spinner } from "../components/ui";
import { api, type Group } from "../lib/api";

export default function Groups() {
  const nav = useNavigate();
  const [groups, setGroups] = useState<Group[] | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [showJoin, setShowJoin] = useState(false);
  const [name, setName] = useState("");
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => api.groups().then(setGroups).catch(() => setGroups([]));
  useEffect(() => {
    load();
  }, []);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const g = await api.createGroup(name.trim());
      nav(`/groups/${g.id}`);
    } finally {
      setBusy(false);
    }
  };

  const join = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const g = await api.acceptInvite(token.trim());
      nav(`/groups/${g.id}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="page-head row between">
        <h1>Groups</h1>
        <div className="row">
          <Button size="sm" onClick={() => setShowJoin(true)}>
            Join
          </Button>
          <Button variant="primary" size="sm" onClick={() => setShowNew(true)}>
            <Icon name="plus" size={16} /> New group
          </Button>
        </div>
      </div>

      {groups === null ? (
        <div style={{ display: "grid", placeItems: "center", padding: 48 }}>
          <Spinner />
        </div>
      ) : groups.length === 0 ? (
        <Card>
          <EmptyState
            title="No groups yet"
            hint="Create a group for your roommates or trip, then add a bill."
          />
        </Card>
      ) : (
        <Card flush>
          {groups.map((g) => (
            <div
              key={g.id}
              className="list-row clickable"
              onClick={() => nav(`/groups/${g.id}`)}
            >
              <span className="avatar">
                <Icon name="users" size={16} />
              </span>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600 }}>{g.name}</div>
                <div className="small muted">{g.currency}</div>
              </div>
              <Icon name="chevron" size={18} />
            </div>
          ))}
        </Card>
      )}

      {showNew && (
        <Modal title="New group" onClose={() => setShowNew(false)}>
          <form onSubmit={create}>
            <Field label="Group name">
              <Input
                autoFocus
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Roommates, Tahoe trip…"
              />
            </Field>
            <Button variant="primary" block type="submit" loading={busy}>
              Create group
            </Button>
          </form>
        </Modal>
      )}

      {showJoin && (
        <Modal title="Join a group" onClose={() => setShowJoin(false)}>
          <form onSubmit={join}>
            <Field label="Invite code" hint="Ask a member to share their group's invite code.">
              <Input
                autoFocus
                required
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="paste code"
              />
            </Field>
            <Button variant="primary" block type="submit" loading={busy}>
              Join group
            </Button>
          </form>
        </Modal>
      )}
    </>
  );
}
