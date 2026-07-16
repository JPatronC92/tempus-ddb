use clap::{Parser, Subcommand};
use serde_json::Value;

#[derive(Parser)]
#[command(name = "tempus-ddb-core")]
#[command(about = "Tempus DDB Core - INTERNAL DEV CLI (Use the Python `tempus` CLI for production)", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Initialize the SQLite database schema
    Init {
        #[arg(long, default_value = "tempus.db")]
        db: String,
    },
    /// Generate a new Ed25519 cryptographic keypair
    GenKeys {
        #[arg(long, default_value = "keys.json")]
        output: String,
    },
    /// Record a new decision in the local ledger
    Record {
        #[arg(long, default_value = "tempus.db")]
        db: String,

        /// JSON payload representing inputs/outputs/decisions
        #[arg(long)]
        payload: String,

        /// JSON rules or rule ID representing the logic applied
        #[arg(long)]
        rules: String,

        /// Path to the keys.json file containing the actor's private key
        #[arg(long, default_value = "keys.json")]
        keyfile: String,

        /// Forces recording this as a genesis decision (no parent required)
        #[arg(long)]
        genesis: bool,
    },
    /// Walk the database to verify the integrity and cryptographic authenticity of the chain
    Validate {
        #[arg(long, default_value = "tempus.db")]
        db: String,
    },
    /// Export all decisions as a JSON array for cloud synchronization
    Export {
        #[arg(long, default_value = "tempus.db")]
        db: String,
    },
    /// List decisions with optional pagination
    List {
        #[arg(long, default_value = "tempus.db")]
        db: String,

        /// Maximum number of records to return
        #[arg(long, default_value = "10")]
        limit: u32,

        /// Number of records to skip
        #[arg(long, default_value = "0")]
        offset: u32,
    },
    /// Count the total number of decisions in the ledger
    Count {
        #[arg(long, default_value = "tempus.db")]
        db: String,
    },
    /// Register an agent in the ledger's identity registry
    RegisterAgent {
        #[arg(long, default_value = "tempus.db")]
        db: String,

        /// Ed25519 public key in hex format (64 hex chars)
        #[arg(long, alias = "public-key")]
        public_key: String,

        /// Human-readable alias for the agent
        #[arg(long)]
        alias: String,

        /// Optional JSON metadata for the agent
        #[arg(long, default_value = "{}")]
        metadata: String,
    },
    /// List all registered agents
    ListAgents {
        #[arg(long, default_value = "tempus.db")]
        db: String,
    },
}

fn main() {
    let cli = Cli::parse();

    match cli.command {
        Commands::Init { db } => {
            match _tempus_ddb::SqliteStorage::new(db.clone(), "keys.json".to_string()) {
                Ok(_) => eprintln!("Database initialized successfully: {}", db),
                Err(e) => {
                    eprintln!("Error: {}", e);
                    std::process::exit(1);
                }
            }
        }
        Commands::GenKeys { output } => {
            match _tempus_ddb::generate_keypair(&output) {
                Ok(json_str) => {
                    eprintln!("Cryptographic keys generated and saved to: {}", output);
                    let val: Value = serde_json::from_str(&json_str).unwrap();
                    println!(
                        "{}",
                        serde_json::to_string(&serde_json::json!({
                            "public_key": val.get("public_key")
                        }))
                        .unwrap()
                    );
                }
                Err(e) => {
                    eprintln!("Error generating keys: {}", e);
                    std::process::exit(1);
                }
            }
        }
        Commands::Record {
            db,
            payload,
            rules,
            keyfile,
            genesis,
        } => {
            let mut storage = match _tempus_ddb::SqliteStorage::new(db, keyfile) {
                Ok(s) => s,
                Err(e) => {
                    eprintln!("Error opening database: {}", e);
                    std::process::exit(1);
                }
            };

            use _tempus_ddb::StorageLayer;
            if let Err(e) = storage.insert_decision(&payload, &rules, genesis) {
                eprintln!("Error recording decision: {}", e);
                std::process::exit(1);
            }

            let latest = storage.get_latest_hash().unwrap_or_default();
            println!(
                "{}",
                serde_json::to_string(&serde_json::json!({
                    "status": "success",
                    "action": "recorded",
                    "latest_hash": latest
                })).unwrap()
            );
        }
        Commands::Validate { db } => {
            let storage = match _tempus_ddb::SqliteStorage::new(db, "keys.json".to_string()) {
                Ok(s) => s,
                Err(e) => {
                    eprintln!("Error opening database: {}", e);
                    std::process::exit(1);
                }
            };

            match storage.validate_ledger() {
                Ok(json) => println!("{}", json),
                Err(e) => {
                    println!("{}", e);
                    std::process::exit(1);
                }
            }
        }
        Commands::Export { db } => {
            let storage = match _tempus_ddb::SqliteStorage::new(db, "keys.json".to_string()) {
                Ok(s) => s,
                Err(e) => {
                    eprintln!("Error opening database: {}", e);
                    std::process::exit(1);
                }
            };

            use _tempus_ddb::StorageLayer;
            match storage.export_ledger() {
                Ok(json) => println!("{}", json),
                Err(e) => {
                    eprintln!("Error exporting ledger: {}", e);
                    std::process::exit(1);
                }
            }
        }
        Commands::List { db, limit, offset } => {
            let storage = match _tempus_ddb::SqliteStorage::new(db, "keys.json".to_string()) {
                Ok(s) => s,
                Err(e) => {
                    eprintln!("Error opening database: {}", e);
                    std::process::exit(1);
                }
            };

            use _tempus_ddb::StorageLayer;
            match storage.list_decisions(limit, offset) {
                Ok(json) => println!("{}", json),
                Err(e) => {
                    eprintln!("Error listing decisions: {}", e);
                    std::process::exit(1);
                }
            }
        }
        Commands::Count { db } => {
            let storage = match _tempus_ddb::SqliteStorage::new(db, "keys.json".to_string()) {
                Ok(s) => s,
                Err(e) => {
                    eprintln!("Error opening database: {}", e);
                    std::process::exit(1);
                }
            };

            use _tempus_ddb::StorageLayer;
            match storage.count_decisions() {
                Ok(count) => println!(
                    "{}",
                    serde_json::to_string(&serde_json::json!({
                        "total_decisions": count
                    })).unwrap()
                ),
                Err(e) => {
                    eprintln!("Error counting decisions: {}", e);
                    std::process::exit(1);
                }
            }
        }
        Commands::RegisterAgent { db, public_key, alias, metadata } => {
            let storage = match _tempus_ddb::SqliteStorage::new(db, "keys.json".to_string()) {
                Ok(s) => s,
                Err(e) => {
                    eprintln!("Error opening database: {}", e);
                    std::process::exit(1);
                }
            };

            match storage.register_agent(&public_key, &alias, &metadata) {
                Ok(json) => println!("{}", json),
                Err(e) => {
                    eprintln!("Error registering agent: {}", e);
                    std::process::exit(1);
                }
            }
        }
        Commands::ListAgents { db } => {
            let storage = match _tempus_ddb::SqliteStorage::new(db, "keys.json".to_string()) {
                Ok(s) => s,
                Err(e) => {
                    eprintln!("Error opening database: {}", e);
                    std::process::exit(1);
                }
            };

            match storage.list_agents() {
                Ok(json) => println!("{}", json),
                Err(e) => {
                    eprintln!("Error listing agents: {}", e);
                    std::process::exit(1);
                }
            }
        }
    }
}
