import { useMemo, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Users } from "lucide-react";
import { toast } from "sonner";
import { userApi } from "@/api/services";
import { apiMessage } from "@/api/client";
import { useAuth } from "@/auth/useAuth";
import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  Field,
  Input,
  LoadingState,
  Modal,
  PageHeader,
  Pagination,
  SearchBox,
  Select,
} from "@/components/ui";
import { titleCase } from "@/lib/format";
import type { Role } from "@/api/types";

export function PeoplePage() {
  const { user } = useAuth();
  const client = useQueryClient();
  const [search, setSearch] = useState("");
  const [role, setRole] = useState<Role | "">("");
  const [offset, setOffset] = useState(0);
  const [open, setOpen] = useState(false);
  const limit = 25;
  const query = useQuery({
    queryKey: ["users", role, offset],
    queryFn: () => userApi.list({ role: role || undefined, offset, limit }),
  });
  const visible = useMemo(
    () =>
      (query.data || []).filter((item) =>
        `${item.full_name} ${item.email}`
          .toLowerCase()
          .includes(search.toLowerCase()),
      ),
    [query.data, search],
  );
  const create = useMutation({
    mutationFn: (payload: {
      full_name: string;
      email: string;
      password: string;
      role: Role;
    }) =>
      payload.role === "staff"
        ? userApi.createStaff(payload)
        : userApi.createCustomer(payload),
    onSuccess: () => {
      toast.success("Account created");
      setOpen(false);
      void client.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (error) => toast.error(apiMessage(error)),
  });
  if (query.isLoading) return <LoadingState />;
  if (query.isError)
    return (
      <ErrorState
        message={apiMessage(query.error)}
        retry={() => void query.refetch()}
      />
    );
  return (
    <>
      <PageHeader
        eyebrow="Identity & access"
        title="People"
        description="Manage customer accounts and the team members who operate your subscription business."
        action={
          <Button onClick={() => setOpen(true)}>
            <Plus size={16} />
            Add person
          </Button>
        }
      />
      <div className="toolbar">
        <SearchBox
          value={search}
          onChange={setSearch}
          placeholder="Search name or email…"
        />
        <div className="toolbar__filters">
          <Select
            value={role}
            onChange={(event) => {
              setRole(event.target.value as Role | "");
              setOffset(0);
            }}
          >
            <option value="">All roles</option>
            <option value="customer">Customers</option>
            <option value="staff">Staff</option>
            <option value="admin">Administrators</option>
          </Select>
        </div>
      </div>
      <section className="card table-card">
        {visible.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Person</th>
                  <th>Role</th>
                  <th>Account ID</th>
                  <th>Access</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((person) => (
                  <tr key={person.id}>
                    <td className="primary-cell">
                      <strong>{person.full_name}</strong>
                      <small>{person.email}</small>
                    </td>
                    <td>
                      <Badge
                        tone={
                          person.role === "admin"
                            ? "info"
                            : person.role === "staff"
                              ? "warning"
                              : "neutral"
                        }
                      >
                        {titleCase(person.role)}
                      </Badge>
                    </td>
                    <td>#{String(person.id).padStart(5, "0")}</td>
                    <td>
                      <Badge tone="success">Active</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon={Users}
            title="No people found"
            text="Try another filter or create the first customer account."
          />
        )}
        <Pagination
          offset={offset}
          limit={limit}
          count={(query.data || []).length}
          onChange={setOffset}
        />
      </section>
      <PersonForm
        open={open}
        admin={user?.role === "admin"}
        loading={create.isPending}
        onClose={() => setOpen(false)}
        onSubmit={(payload) => create.mutate(payload)}
      />
    </>
  );
}
function PersonForm({
  open,
  admin,
  loading,
  onClose,
  onSubmit,
}: {
  open: boolean;
  admin: boolean;
  loading: boolean;
  onClose: () => void;
  onSubmit: (value: {
    full_name: string;
    email: string;
    password: string;
    role: Role;
  }) => void;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("customer");
  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit({ full_name: name, email, password, role });
  };
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Create a new account"
      description="Invite a customer or give a team member operational access."
    >
      <form onSubmit={submit}>
        <div className="form-grid">
          <Field label="Full name">
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </Field>
          <Field label="Email address">
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </Field>
          <Field
            label="Temporary password"
            hint="12+ characters, uppercase, lowercase, number and symbol."
          >
            <Input
              type="password"
              minLength={12}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </Field>
          <Field label="Account role">
            <Select
              value={role}
              onChange={(e) => setRole(e.target.value as Role)}
            >
              <option value="customer">Customer</option>
              {admin && <option value="staff">Staff</option>}
            </Select>
          </Field>
        </div>
        <div className="form-actions">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={loading}>
            Create account
          </Button>
        </div>
      </form>
    </Modal>
  );
}
