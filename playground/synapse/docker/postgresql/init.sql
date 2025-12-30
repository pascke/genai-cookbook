create extension if not exists "vector";

create table agents(
    id uuid not null,
    name varchar(80) not null,
    description varchar(255),
    instructions text,
    model jsonb not null,
    primary key (id)
);

create table sessions(
    id uuid not null,
    created_at timestamp with time zone not null default current_timestamp,
    updated_at timestamp with time zone not null default current_timestamp,
    primary key (id)
);

create table messages(
    id uuid not null,
    session_id uuid not null,
    content text not null,
    labels jsonb,
    created_at timestamp with time zone not null default current_timestamp,
    primary key (id),
    constraint messages_session_id_fkey foreign key (session_id) references sessions(id)
);

create index messages_session_time_idx on messages using btree (session_id, created_at);

create table nested_agents (
    agent_id uuid not null,
    sub_agent_id uuid not null,
    created_at timestamp with time zone not null default current_timestamp,
    primary key (agent_id, sub_agent_id),
    foreign key (agent_id) references agents (id),
    foreign key (sub_agent_id) references agents (id)
);

create index nested_agents_agent_id_idx on nested_agents using btree (agent_id);

create table knowledge_groups(
    id uuid not null,
    name varchar(80) not null,
    description varchar(255),
    primary key (id)
);

create table knowledge_bases(
    id uuid not null,
    knowledge_group_id uuid not null,
    name varchar(80) not null,
    content text not null,
    embedding vector(1536) not null,
    primary key (id),
    foreign key (knowledge_group_id) references knowledge_groups (id)
);

create index knowledge_bases_knowledge_group_id_idx on knowledge_bases using btree (knowledge_group_id);
create index knowledge_bases_embedding_hnsw_cos_idx on knowledge_bases using hnsw (embedding vector_cosine_ops) WITH (m='16', ef_construction='64');