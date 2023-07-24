from gql import gql

query_get_pixel_10x = gql(
    """
  mutation pixelHistory($input1: ActInput!, $input2: ActInput!, $input3: ActInput!, $input4: ActInput!, $input5: ActInput!, $input6: ActInput!, $input7: ActInput!, $input8: ActInput!, $input9: ActInput!, $input10: ActInput!) {
    input1: act(input: $input1) {
      data {
        ... on BasicMessage {
          id
          data {
            ... on GetTileHistoryResponseMessageData {
              lastModifiedTimestamp
              userInfo {
                userID
                username
              }
            }
          }
        }
      }
    }
    input2: act(input: $input2) {
      data {
        ... on BasicMessage {
          id
          data {
            ... on GetTileHistoryResponseMessageData {
              lastModifiedTimestamp
              userInfo {
                userID
                username
              }
            }
          }
        }
      }
    }
    input3: act(input: $input3) {
      data {
        ... on BasicMessage {
          id
          data {
            ... on GetTileHistoryResponseMessageData {
              lastModifiedTimestamp
              userInfo {
                userID
                username
              }
            }
          }
        }
      }
    }
    input4: act(input: $input4) {
      data {
        ... on BasicMessage {
          id
          data {
            ... on GetTileHistoryResponseMessageData {
              lastModifiedTimestamp
              userInfo {
                userID
                username
              }
            }
          }
        }
      }
    }
    input5: act(input: $input5) {
      data {
        ... on BasicMessage {
          id
          data {
            ... on GetTileHistoryResponseMessageData {
              lastModifiedTimestamp
              userInfo {
                userID
                username
              }
            }
          }
        }
      }
    }
    input6: act(input: $input6) {
      data {
        ... on BasicMessage {
          id
          data {
            ... on GetTileHistoryResponseMessageData {
              lastModifiedTimestamp
              userInfo {
                userID
                username
              }
            }
          }
        }
      }
    }
    input7: act(input: $input7) {
      data {
        ... on BasicMessage {
          id
          data {
            ... on GetTileHistoryResponseMessageData {
              lastModifiedTimestamp
              userInfo {
                userID
                username
              }
            }
          }
        }
      }
    }
    input8: act(input: $input8) {
      data {
        ... on BasicMessage {
          id
          data {
            ... on GetTileHistoryResponseMessageData {
              lastModifiedTimestamp
              userInfo {
                userID
                username
              }
            }
          }
        }
      }
    }
    input9: act(input: $input9) {
      data {
        ... on BasicMessage {
          id
          data {
            ... on GetTileHistoryResponseMessageData {
              lastModifiedTimestamp
              userInfo {
                userID
                username
              }
            }
          }
        }
      }
    }
    input10: act(input: $input10) {
      data {
        ... on BasicMessage {
          id
          data {
            ... on GetTileHistoryResponseMessageData {
              lastModifiedTimestamp
              userInfo {
                userID
                username
              }
            }
          }
        }
      }
    }
  }
 """
)

socket_key = "socket:snakebin"

config_gql = gql(
    """
  subscription configuration($input: SubscribeInput!) {
    subscribe(input: $input) {
      id
      ... on BasicMessage {
        data {
          __typename
          ... on ConfigurationMessageData {
            colorPalette {
              colors {
                hex
                index
                __typename
              }
              __typename
            }
            canvasConfigurations {
              index
              dx
              dy
              __typename
            }
            activeZone {
              topLeft {
                x
                y
                __typename
              }
              bottomRight {
                x
                y
                __typename
              }
              __typename
            }
            canvasWidth
            canvasHeight
            adminConfiguration {
              maxAllowedCircles
              maxUsersPerAdminBan
              __typename
            }
            __typename
          }
        }
        __typename
      }
      __typename
    }
  }
  """
)

sub_gql = gql(
    """
  subscription replace($input: SubscribeInput!) {
    subscribe(input: $input) {
      id
      ... on BasicMessage {
        data {
          __typename
          ... on FullFrameMessageData {
            __typename
            name
            timestamp
          }
          ... on DiffFrameMessageData {
            __typename
            name
            currentTimestamp
            previousTimestamp
          }
        }
      }
    }
  }"""
)
