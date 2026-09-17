const { ApolloServer, gql } = require("apollo-server");
const resolvers = require("./resolvers");

const typeDefs = gql`
  type Query {
    user(id: ID!): User
  }
  type User {
    id: ID!
    friends: [User!]!
    posts: [Post!]!
  }
  type Post {
    id: ID!
    comments: [Comment!]!
  }
  type Comment {
    id: ID!
    author: User!
  }
  type Mutation {
    login(email: String!, password: String!): String
  }
`;

const server = new ApolloServer({ typeDefs, resolvers });
server.listen(4000);
